from __future__ import annotations

import asyncio
import time
from typing import Any

from . import analytics, config, extract, insights, ryo
from .tickers import parse_symbol
from .truenorth import TrueNorth, market_pack

_PACK: dict[str, tuple[float, tuple[dict[str, Any], ...]]] = {}
_PACK_LOCK = asyncio.Lock()
_PACK_REFRESHING: set[str] = set()
_TN: tuple[float, dict[str, Any]] | None = None
_TN_REFRESHING = False


def setup() -> dict[str, Any]:
    return {
        "ryo": config.ryo_configured(),
        "truenorth": config.truenorth_configured(),
        "llm": config.llm_configured(),
        "provider": config.llm_provider(),
    }


def _derived_book(overview: dict[str, Any]) -> tuple[Any, Any, float | None, float | None]:
    totals = overview.get("totals") if isinstance(overview.get("totals"), dict) else {}
    vol = totals.get("total_volume_24h_usd")
    cap = totals.get("total_market_cap_usd")
    turnover = (vol / cap) if isinstance(vol, (int, float)) and isinstance(cap, (int, float)) and cap else None
    rest_dom = None
    if overview.get("btc_dominance") is not None:
        rest_dom = 100.0 - overview["btc_dominance"] - (overview.get("eth_dominance") or 0)
    return vol, cap, turnover, rest_dom


def _kick_truenorth() -> None:
    global _TN_REFRESHING
    if _TN_REFRESHING:
        return
    _TN_REFRESHING = True

    async def _run() -> None:
        global _TN, _TN_REFRESHING
        try:
            tn = TrueNorth(ryo.http())
            second = await asyncio.wait_for(market_pack(tn), timeout=8)
            _TN = (time.time(), second)
        except Exception:
            pass
        finally:
            _TN_REFRESHING = False

    try:
        asyncio.get_running_loop().create_task(_run())
    except RuntimeError:
        _TN_REFRESHING = False


def _pack_key(scan_n: int, extra: str | None) -> str:
    return f"{scan_n}:{extra or ''}"


async def _fetch_market_live(scan_n: int, extra: str | None) -> tuple[dict[str, Any], ...]:
    client = ryo.http()
    jobs = [
        ryo.call_tool(client, "market_overview", {}),
        ryo.call_tool(client, "monitor_market_sentiment_shift", {"time_window": "7d"}),
        ryo.call_tool(client, "scan_market", {"top_n": scan_n}),
    ]
    if extra:
        jobs.append(ryo.call_tool(client, "analyze_token", {"symbol": extra}))
    return tuple(await asyncio.gather(*jobs))


def _kick_pack(scan_n: int, extra: str | None) -> None:
    key = _pack_key(scan_n, extra)
    if key in _PACK_REFRESHING:
        return
    _PACK_REFRESHING.add(key)

    async def _run() -> None:
        try:
            live = await _fetch_market_live(scan_n, extra)
            _PACK[key] = (time.time(), live)
        except Exception:
            pass
        finally:
            _PACK_REFRESHING.discard(key)

    try:
        asyncio.get_running_loop().create_task(_run())
    except RuntimeError:
        _PACK_REFRESHING.discard(key)


async def _fetch_market(scan_n: int = 12, extra: str | None = None) -> tuple[dict[str, Any], ...]:
    key = _pack_key(scan_n, extra)
    hit = _PACK.get(key)
    now = time.time()
    if hit and now - hit[0] < config.RYO_CACHE_TTL:
        return hit[1]
    if hit and now - hit[0] < config.RYO_SWR_TTL:
        _kick_pack(scan_n, extra)
        return tuple({**env, "stale": True} for env in hit[1])
    async with _PACK_LOCK:
        hit = _PACK.get(key)
        now = time.time()
        if hit and now - hit[0] < config.RYO_CACHE_TTL:
            return hit[1]
        live = await _fetch_market_live(scan_n, extra)
        _PACK[key] = (time.time(), live)
        return live


def _assemble_market(
    overview_env: dict[str, Any],
    sentiment_env: dict[str, Any],
    scan_env: dict[str, Any],
    *,
    btc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    overview = extract.extract_overview(overview_env)
    sentiment = extract.extract_sentiment(sentiment_env)
    scan_rows = _screener_rows(scan_env)
    movers = _movers(overview_env)
    chart = _volume_chart(scan_rows)
    vol, cap, turnover, rest_dom = _derived_book(overview)
    stress = analytics.positioning_stress(overview, sentiment, btc)
    cards = insights.gap_cards(stress) + insights.market_cards(overview, sentiment, scan_rows)
    return {
        "ok": True,
        "overview": overview,
        "sentiment": sentiment,
        "gainers": movers["gainers"],
        "losers": movers["losers"],
        "chart": chart,
        "volume_24h": vol,
        "market_cap": cap,
        "turnover": turnover,
        "rest_dominance": rest_dom,
        "most_active": chart[0] if chart else None,
        "stress": stress,
        "insights": cards,
        "scan": scan_rows,
        "spikes": [r for r in scan_rows if r.get("spike")],
        "stale": bool(overview_env.get("stale") or sentiment_env.get("stale") or scan_env.get("stale")),
        "headline": overview.get("headline") or sentiment.get("headline"),
        "as_of": overview.get("as_of") or sentiment.get("as_of"),
    }


async def load_overview() -> dict[str, Any]:
    if not config.ryo_configured():
        return {"ok": False, "error": "RYO_MCP_KEY is not set."}
    overview_env, sentiment_env, scan_env = await _fetch_market(12)
    return _assemble_market(overview_env, sentiment_env, scan_env)


async def load_screener(top_n: int = 12) -> dict[str, Any]:
    if not config.ryo_configured():
        return {"ok": False, "error": "RYO_MCP_KEY is not set."}
    scan_env = await ryo.call_tool(ryo.http(), "scan_market", {"top_n": top_n})
    table = _screener_rows(scan_env)
    table.sort(key=lambda r: abs(r.get("change_24h") or 0), reverse=True)
    meta = extract.extract_scan_meta(scan_env)
    return {
        "ok": True,
        "rows": table,
        "meta": meta,
        "headline": meta.get("headline") or extract.summary_of(scan_env).get("headline"),
        "selection_method": meta.get("selection_method"),
        "stale": bool(scan_env.get("stale")),
        "status": extract.status_of(scan_env),
        "as_of": meta.get("as_of"),
        "spikes": [r for r in table if r.get("spike")],
    }


async def _deep_or_none(client: Any, symbol: str) -> dict[str, Any] | None:
    try:
        return await asyncio.wait_for(
            ryo.call_tool(client, "deep_analysis", {"symbol": symbol, "include_perp": False}),
            timeout=20,
        )
    except asyncio.TimeoutError:
        return None


async def load_token(symbol: str) -> dict[str, Any]:
    parsed = parse_symbol(symbol)
    if not parsed["ok"] or parsed.get("empty"):
        return {"ok": False, "error": parsed.get("error") or "Enter a ticker.", "code": parsed.get("code")}
    canon = parsed["symbol"]
    client = ryo.http()
    analyze_env, deep_env = await asyncio.gather(
        ryo.call_tool(client, "analyze_token", {"symbol": canon}),
        _deep_or_none(client, canon),
    )
    token = extract.extract_token(analyze_env, fallback_symbol=canon)
    if token.get("price") is None:
        return {
            "ok": False,
            "error": f"{canon} is not a live ticker on this book.",
            "code": "unknown_ticker",
            "symbol": canon,
            "status": extract.status_of(analyze_env),
            "warnings": extract.warnings_of(analyze_env),
        }
    deep = extract.extract_deep(deep_env, canon)
    if not deep_env:
        deep["headline"] = "Deep pack timed out — showing the fast read."
    deep_market = deep.get("market") if isinstance(deep.get("market"), dict) else {}
    if token.get("mcap") is None and deep_market.get("mcap") is not None:
        token["mcap"] = deep_market["mcap"]
    return {
        "ok": True,
        "symbol": canon,
        "token": token,
        "deep": deep,
        "structure": {
            "mcap": token.get("mcap"),
            "fdv": token.get("fdv"),
            "volume": token.get("volume"),
            "turnover": token.get("turnover"),
            "dilution": token.get("dilution"),
            "dominance_pct": deep_market.get("dominance_pct"),
            "circulating_supply": deep_market.get("circulating_supply"),
            "max_supply": deep_market.get("max_supply"),
            "rank": token.get("rank"),
            "chain": token.get("chain"),
            "contract": token.get("contract"),
        },
        "insights": insights.token_cards(token, deep),
        "stale": bool(analyze_env.get("stale") or (deep_env or {}).get("stale")),
        "as_of": token.get("as_of") or deep.get("as_of"),
    }


async def load_compare(symbols: str) -> dict[str, Any]:
    raw = [parse_symbol(part.strip()).get("symbol") for part in (symbols or "").replace(";", ",").split(",") if part.strip()]
    names = [s for s in raw if s]
    if len(names) < 2:
        return {"ok": False, "error": "Enter two to four tickers, e.g. SOL, ORCA, CFG.", "symbols": names}
    names = names[:4]
    env = await ryo.call_tool(ryo.http(), "compare_tokens", {"symbols": ", ".join(names), "intent": "swing"})
    view = extract.extract_compare(env)
    return {"ok": True, "symbols": names, "compare": view, "stale": bool(env.get("stale")), "as_of": view.get("as_of")}


async def load_analytics() -> dict[str, Any]:
    global _TN
    if not config.ryo_configured():
        return {"ok": False, "error": "RYO_MCP_KEY is not set."}
    overview_env, sentiment_env, scan_env = await _fetch_market(12)
    btc_env = await ryo.call_tool(ryo.http(), "analyze_token", {"symbol": "BTC"})
    btc = extract.extract_token(btc_env, fallback_symbol="BTC")
    pack = _assemble_market(overview_env, sentiment_env, scan_env, btc=btc)
    second: dict[str, Any] | None = None
    if config.truenorth_configured():
        now = time.time()
        if _TN and now - _TN[0] < config.RYO_CACHE_TTL:
            second = _TN[1]
        else:
            second = _TN[1] if _TN else None
            _kick_truenorth()
    pack["btc"] = btc
    pack["second_book"] = second
    pack["headline"] = ((pack.get("stress") or {}).get("gap") or {}).get("label") or pack.get("headline")
    pack["stale"] = bool(pack.get("stale") or btc_env.get("stale"))
    return pack


async def load_ryo_catalog() -> dict[str, Any]:
    if not config.ryo_configured():
        return {"ok": False, "error": "RYO_MCP_KEY is not set."}
    client = ryo.http()
    try:
        payload = await ryo.catalog(client)
    except ryo.RyoError as exc:
        try:
            me = await ryo.whoami(client)
        except Exception:
            return {"ok": False, "error": str(exc), "code": exc.code}
        tools = me.get("tools")
        if not tools:
            return {"ok": False, "error": str(exc), "code": exc.code}
        return {"ok": True, "source": "whoami", "catalog": {"tools": tools}, "tools": tools}
    tools = payload.get("tools") if isinstance(payload.get("tools"), list) else payload.get("data") or payload
    return {"ok": True, "source": "tools", "catalog": payload, "tools": tools}


async def load_ryo_whoami() -> dict[str, Any]:
    if not config.ryo_configured():
        return {"ok": False, "error": "RYO_MCP_KEY is not set."}
    try:
        payload = await ryo.whoami(ryo.http())
    except ryo.RyoError as exc:
        return {"ok": False, "error": str(exc), "code": exc.code}
    blocked = {"key", "token", "secret", "authorization", "api_key"}
    safe = {k: v for k, v in payload.items() if str(k).lower() not in blocked}
    return {"ok": True, "whoami": safe}


def _screener_rows(scan_env: dict[str, Any]) -> list[dict[str, Any]]:
    table = []
    for row in extract.extract_candidates(scan_env, None):
        raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
        vol = raw.get("volume_24h_usd")
        cap = raw.get("market_cap_usd")
        chg = raw.get("change_24h_pct")
        turn = raw.get("turnover_ratio")
        if not isinstance(turn, (int, float)):
            turn = (vol / cap) if isinstance(vol, (int, float)) and isinstance(cap, (int, float)) and cap else None
        table.append(
            {
                "rank": raw.get("rank"),
                "symbol": row.get("symbol"),
                "name": raw.get("name") or row.get("symbol"),
                "chain": raw.get("chain"),
                "contract": raw.get("contract"),
                "price": raw.get("price_usd"),
                "change_24h": chg,
                "volume": vol,
                "market_cap": cap,
                "turnover": turn,
                "momentum": raw.get("momentum_score"),
                "established": raw.get("established_asset"),
                "spike": bool((chg is not None and abs(float(chg)) >= 80) or (turn is not None and turn >= 1)),
                "reason": row.get("note") or raw.get("reason"),
                "source": row.get("source"),
            }
        )
    return table


def _volume_chart(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chart = [{"symbol": r.get("symbol"), "volume": r.get("volume"), "market_cap": r.get("market_cap")} for r in rows if r.get("volume")]
    chart.sort(key=lambda r: r["volume"] or 0, reverse=True)
    chart = chart[:7]
    if not chart:
        return []
    max_vol = max((r["volume"] or 0) for r in chart) or 1
    max_cap = max((r["market_cap"] or 0) for r in chart) or 1
    for row in chart:
        row["vol_pct"] = max(4, min(100, ((row["volume"] or 0) / max_vol) * 100))
        row["cap_pct"] = max(4, min(100, ((row["market_cap"] or 0) / max_cap) * 100)) if row.get("market_cap") else 4
    return chart


def _movers(overview_env: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    data = extract.data_of(overview_env)
    block = data.get("top_movers") if isinstance(data.get("top_movers"), dict) else {}
    out: dict[str, list[dict[str, Any]]] = {"gainers": [], "losers": []}
    for key in ("gainers", "losers"):
        rows = block.get(key) if isinstance(block.get(key), list) else []
        for row in rows[:6]:
            if not isinstance(row, dict):
                continue
            out[key].append(
                {
                    "symbol": row.get("symbol"),
                    "name": row.get("name"),
                    "price": row.get("price_usd"),
                    "change_24h": row.get("change_24h_pct"),
                }
            )
    return out
