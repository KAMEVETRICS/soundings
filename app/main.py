from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from . import formatters
from .claw import answer as claw_answer
from .services import (
    load_analytics,
    load_compare,
    load_overview,
    load_ryo_catalog,
    load_ryo_whoami,
    load_screener,
    load_token,
    setup,
)

ROOT = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(ROOT / "templates"))
templates.env.filters["money"] = formatters.money
templates.env.filters["pct"] = formatters.pct
templates.env.filters["usd"] = formatters.usd_compact

app = FastAPI(title="Soundings", version="0.3.0")
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")
api = APIRouter(prefix="/api", tags=["data"])


def _ctx(request: Request, **extra: Any) -> dict[str, Any]:
    return {"request": request, "setup": setup(), "nav": extra.pop("nav", ""), **extra}


def _json(data: dict[str, Any], *, error_status: int = 503) -> JSONResponse:
    if data.get("ok") is False:
        return JSONResponse(data, status_code=error_status)
    return JSONResponse(data)


@app.get("/", response_class=HTMLResponse)
async def overview(request: Request) -> HTMLResponse:
    data = await load_overview()
    return templates.TemplateResponse(request, "overview.html", _ctx(request, nav="overview", data=data))


@app.get("/screener", response_class=HTMLResponse)
async def screener(request: Request) -> HTMLResponse:
    data = await load_screener()
    return templates.TemplateResponse(request, "screener.html", _ctx(request, nav="screener", data=data))


@app.get("/token/{symbol}", response_class=HTMLResponse)
async def token_page(request: Request, symbol: str) -> HTMLResponse:
    data = await load_token(symbol)
    return templates.TemplateResponse(request, "token.html", _ctx(request, nav="screener", data=data))


@app.get("/sentiment", response_class=HTMLResponse)
async def sentiment_page(request: Request) -> HTMLResponse:
    data = await load_overview()
    return templates.TemplateResponse(request, "sentiment.html", _ctx(request, nav="sentiment", data=data))


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request) -> HTMLResponse:
    data = await load_analytics()
    return templates.TemplateResponse(request, "analytics.html", _ctx(request, nav="analytics", data=data))


@app.get("/insights", response_class=HTMLResponse)
async def insights_page(request: Request) -> HTMLResponse:
    data = await load_overview()
    return templates.TemplateResponse(request, "insights.html", _ctx(request, nav="insights", data=data))


@app.get("/compare", response_class=HTMLResponse)
async def compare_page(request: Request, symbols: str = "SOL, ETH, BTC") -> HTMLResponse:
    data = await load_compare(symbols)
    data["query"] = symbols
    return templates.TemplateResponse(request, "compare.html", _ctx(request, nav="compare", data=data))


@app.get("/claw", response_class=HTMLResponse)
async def claw_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "claw.html", _ctx(request, nav="claw"))


class ClawBody(BaseModel):
    question: str = Field(min_length=3, max_length=500)


def _api_index() -> dict[str, Any]:
    return {
        "ok": True,
        "name": "Soundings",
        "setup": setup(),
        "pages": ["/", "/analytics", "/screener", "/sentiment", "/compare", "/insights", "/claw"],
        "endpoints": [
            "GET /api/health",
            "GET /api/catalog",
            "GET /api/whoami",
            "GET /api/overview",
            "GET /api/analytics",
            "GET /api/screener?top_n=",
            "GET /api/token/{symbol}",
            "GET /api/compare?symbols=",
            "POST /api/claw",
        ],
    }


@app.get("/api", include_in_schema=False)
async def api_index_plain() -> dict[str, Any]:
    return _api_index()


@api.get("/")
async def api_index() -> dict[str, Any]:
    return _api_index()


@api.get("/health")
async def health() -> dict[str, Any]:
    return {"ok": True, "soundings": "ok", "setup": setup()}


@api.get("/catalog")
async def api_catalog() -> JSONResponse:
    return _json(await load_ryo_catalog())


@api.get("/whoami")
async def api_whoami() -> JSONResponse:
    return _json(await load_ryo_whoami())


@api.get("/overview")
async def api_overview() -> JSONResponse:
    return _json(await load_overview())


@api.get("/analytics")
async def api_analytics() -> JSONResponse:
    return _json(await load_analytics())


@api.get("/screener")
async def api_screener(top_n: int = Query(default=12, ge=1, le=16)) -> JSONResponse:
    return _json(await load_screener(top_n=top_n))


@api.get("/token/{symbol}")
async def api_token(symbol: str) -> JSONResponse:
    return _json(await load_token(symbol), error_status=400)


@api.get("/compare")
async def api_compare(symbols: str = Query(default="SOL,ETH,BTC")) -> JSONResponse:
    return _json(await load_compare(symbols), error_status=400)


@api.post("/claw")
async def api_claw(body: ClawBody) -> JSONResponse:
    result = await claw_answer(body.question)
    return JSONResponse(result, status_code=200 if result.get("ok") else 400)


app.include_router(api)
