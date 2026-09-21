from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from openai import OpenAI

from . import config, extract, ryo
from .tickers import parse_symbol

SYSTEM = """You are Soundings Claw, a read-only market clerk.
Answer only from the evidence JSON. Never invent prices or RSI.
If a field is missing, say so. This is not financial advice.
Keep the answer under 180 words. Start with what changed and why it matters."""


def _llm() -> OpenAI | None:
    if config.llm_provider() != "openrouter":
        if not config.XAI_API_KEY:
            return None
        return OpenAI(api_key=config.XAI_API_KEY, base_url="https://api.x.ai/v1")
    return OpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL,
        default_headers={"HTTP-Referer": "http://127.0.0.1:8001", "X-Title": "Soundings"},
    )


def _guess_symbol(question: str) -> str | None:
    for token in re.findall(r"\b[A-Za-z][A-Za-z0-9]{1,10}\b", question or ""):
        parsed = parse_symbol(token)
        if parsed.get("ok") and parsed.get("symbol") and parsed["symbol"] not in {"THE", "AND", "FOR", "WHAT", "WHY", "HOW"}:
            if parsed["symbol"] in {"BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "AVAX", "LINK", "ORCA", "RAY", "CFG"}:
                return parsed["symbol"]
    return None


async def answer(question: str) -> dict[str, Any]:
    question = (question or "").strip()
    if not question:
        return {"ok": False, "error": "Ask a market question."}
    if not config.ryo_configured():
        return {"ok": False, "error": "RYO_MCP_KEY is not set."}
    symbol = _guess_symbol(question)
    client = ryo.http()
    overview = await ryo.call_tool(client, "market_overview", {})
    sentiment = await ryo.call_tool(client, "monitor_market_sentiment_shift", {"time_window": "7d"})
    token = None
    if symbol:
        token = await ryo.call_tool(client, "analyze_token", {"symbol": symbol})
    evidence = {
        "overview": extract.extract_overview(overview),
        "sentiment": extract.extract_sentiment(sentiment),
        "token": extract.extract_token(token, fallback_symbol=symbol) if token else None,
        "question": question,
    }
    client_llm = _llm()
    if client_llm is None:
        headline = (evidence["overview"] or {}).get("headline") or "No model key."
        return {
            "ok": True,
            "symbol": symbol,
            "answer": f"{headline} Model key missing, so Claw is quoting the RYO headline only.",
            "evidence": evidence,
            "model": None,
        }
    try:
        response = await asyncio.to_thread(
            lambda: client_llm.chat.completions.create(
                model=config.chamber_model(),
                temperature=0.2,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": json.dumps(evidence, default=str)[:10000]},
                ],
            )
        )
        text = (response.choices[0].message.content or "").strip()
    except Exception as exc:
        text = f"Model failed ({exc}). Regime: {(evidence['overview'] or {}).get('headline')}"
    return {"ok": True, "symbol": symbol, "answer": text, "evidence": evidence, "model": config.chamber_model()}
