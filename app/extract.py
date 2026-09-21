from __future__ import annotations

from typing import Any


def dig(obj: Any, *paths: str) -> Any:
    """Return the first present value among dotted paths. Missing is None, never 0."""
    for path in paths:
        cur: Any = obj
        ok = True
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                ok = False
                break
        if ok and cur is not None and cur != "":
            return cur
    return None


def as_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        if number != number or number in (float("inf"), float("-inf")):
            return None
        return number
    if isinstance(value, str):
        text = value.strip().replace("%", "").replace(",", "")
        if not text:
            return None
        try:
            number = float(text)
        except ValueError:
            return None
        if number != number:
            return None
        return number
    return None


def as_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, (int, float, bool)):
        return str(value)
    return None


def result_of(envelope: dict[str, Any] | None) -> dict[str, Any] | None:
    if not envelope:
        return None
    result = envelope.get("result")
    return result if isinstance(result, dict) else None


def data_of(envelope: dict[str, Any] | None) -> dict[str, Any]:
    result = result_of(envelope)
    if not result:
        return {}
    data = result.get("data")
    return data if isinstance(data, dict) else {}


def summary_of(envelope: dict[str, Any] | None) -> dict[str, Any]:
    result = result_of(envelope)
    if not result:
        return {}
    summary = result.get("summary")
    if isinstance(summary, dict):
        return summary
    if isinstance(summary, str):
        return {"headline": summary}
    return {}


def status_of(envelope: dict[str, Any] | None) -> str:
    result = result_of(envelope)
    if not result:
        return "unavailable"
    status = result.get("status")
    if status in {"ok", "partial", "unavailable"}:
        return status
    return "unavailable" if not envelope or not envelope.get("ok") else "ok"


def data_mode_of(envelope: dict[str, Any] | None) -> str:
    result = result_of(envelope)
    if not result:
        return "unknown"
    mode = result.get("data_mode")
    if mode in {"live", "mixed", "simulated", "unknown"}:
        return mode
    return "unknown"


def warnings_of(envelope: dict[str, Any] | None) -> list[str]:
    result = result_of(envelope)
    if not result:
        err = (envelope or {}).get("error") or {}
        msg = err.get("message")
        return [str(msg)] if msg else []
    warnings = result.get("warnings") or []
    if isinstance(warnings, list):
        out: list[str] = []
        for item in warnings:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, dict):
                text = item.get("message") or item.get("text")
                if text:
                    out.append(str(text))
        return out
    if isinstance(warnings, str):
        return [warnings]
    return []


def _iter_rows(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("candidates", "tokens", "results", "ranked", "items", "movers", "gainers", "top", "list"):
        rows = payload.get(key)
        if isinstance(rows, list):
            return rows
    return []


def extract_symbol(row: Any) -> str | None:
    if isinstance(row, str):
        text = row.strip().upper()
        return text or None
    if not isinstance(row, dict):
        return None
    raw = dig(row, "symbol", "asset.symbol", "ticker", "token", "name", "id")
    text = as_text(raw)
    if not text:
        return None
    return text.split("/")[0].split("-")[0].strip().upper()


def extract_candidates(scan_envelope: dict[str, Any] | None, overview_envelope: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows = _iter_rows(data_of(scan_envelope))
    if not rows:
        result = result_of(scan_envelope) or {}
        rows = _iter_rows(result)
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        symbol = extract_symbol(row)
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        note = None
        if isinstance(row, dict):
            note = as_text(dig(row, "reason", "why", "note", "thesis", "summary", "comment"))
        candidates.append({"symbol": symbol, "source": "scan_market", "note": note, "raw": row if isinstance(row, dict) else {"value": row}})
    if candidates:
        return candidates[:16]

    # Fallback: movers from market_overview, still real evidence, never invented.
    overview_data = data_of(overview_envelope)
    mover_rows: list[Any] = []
    for key in ("gainers", "top_gainers", "topGainers", "movers", "top_movers"):
        block = overview_data.get(key)
        mover_rows.extend(_iter_rows(block) if not isinstance(block, list) else block)
    for row in mover_rows:
        symbol = extract_symbol(row)
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        candidates.append({"symbol": symbol, "source": "market_overview.movers", "note": "fallback from overview movers after scan was empty", "raw": row if isinstance(row, dict) else {"value": row}})
        if len(candidates) >= 8:
            break
    return candidates


def extract_overview(envelope: dict[str, Any] | None) -> dict[str, Any]:
    data = data_of(envelope)
    summary = summary_of(envelope)
    market = data.get("market") if isinstance(data.get("market"), dict) else {}
    sentiment = data.get("sentiment") if isinstance(data.get("sentiment"), dict) else {}
    details = market.get("breadth_details") if isinstance(market.get("breadth_details"), dict) else {}
    regime = dig(data, "regime", "market_regime", "phase")
    fear = as_number(dig(sentiment, "fear_greed_index", "value", "score")) or as_number(dig(data, "fear_greed_index"))
    fear_label = as_text(dig(sentiment, "label")) 
    advancing = as_number(details.get("advancing"))
    declining = as_number(details.get("declining"))
    unchanged = as_number(details.get("unchanged"))
    breadth_ratio = as_number(market.get("breadth"))
    breadth_text = None
    if advancing is not None and declining is not None:
        breadth_text = f"{int(advancing)} advancing / {int(declining)} declining"
    result = result_of(envelope) or {}
    return {
        "status": status_of(envelope),
        "data_mode": data_mode_of(envelope),
        "as_of": dig(result, "as_of"),
        "headline": as_text(summary.get("headline")) if summary else None,
        "points": flatten_points(summary.get("key_points") or summary.get("points")),
        "regime": as_text(regime) if not isinstance(regime, dict) else as_text(dig(regime, "label", "name", "status")),
        "fear_greed": fear,
        "fear_greed_label": fear_label,
        "breadth": breadth_text or breadth_ratio,
        "breadth_ratio": breadth_ratio,
        "breadth_method": as_text(details.get("method")),
        "btc_dominance": as_number(market.get("btc_dominance_pct")),
        "eth_dominance": as_number(market.get("eth_dominance_pct")),
        "mcap_change_24h": as_number(market.get("market_cap_change_24h_pct")),
        "total_market_cap_usd": as_number(market.get("total_market_cap_usd")),
        "total_volume_24h_usd": as_number(market.get("total_volume_24h_usd")),
        "advancing": int(advancing) if advancing is not None else None,
        "declining": int(declining) if declining is not None else None,
        "unchanged": int(unchanged) if unchanged is not None else None,
        "universe": int(as_number(details.get("universe_size")) or 0) or None,
        "totals": market or None,
        "availability": result.get("availability") if isinstance(result.get("availability"), dict) else None,
        "warnings": warnings_of(envelope),
        "stale": bool((envelope or {}).get("stale")),
    }


def extract_sentiment(envelope: dict[str, Any] | None) -> dict[str, Any]:
    data = data_of(envelope)
    summary = summary_of(envelope)
    evidence = data.get("evidence") if isinstance(data.get("evidence"), dict) else {}
    fear = evidence.get("fear_greed") if isinstance(evidence.get("fear_greed"), dict) else {}
    headline = as_text(summary.get("headline")) or as_text(data.get("summary"))
    change_pts = as_number(fear.get("change_7d_points"))
    shift = None
    if change_pts is not None:
        direction = as_text(fear.get("change_direction")) or ("up" if change_pts > 0 else "down" if change_pts < 0 else "flat")
        shift = f"{direction} {change_pts:+.0f} pts over 7d"
    fund = evidence.get("funding") if isinstance(evidence.get("funding"), dict) else {}
    current_win = fund.get("current_7d_window") if isinstance(fund.get("current_7d_window"), dict) else {}
    previous_win = fund.get("previous_7d_window") if isinstance(fund.get("previous_7d_window"), dict) else {}
    liq = evidence.get("liquidation") if isinstance(evidence.get("liquidation"), dict) else {}
    alt = evidence.get("altseason") if isinstance(evidence.get("altseason"), dict) else {}
    result = result_of(envelope) or {}
    return {
        "status": status_of(envelope),
        "data_mode": data_mode_of(envelope),
        "as_of": dig(result, "as_of") or as_text(data.get("observation_as_of")),
        "headline": headline,
        "points": flatten_points(summary.get("key_points") or summary.get("points")),
        "shift": shift,
        "fear_greed": as_number(fear.get("value")),
        "fear_greed_label": as_text(fear.get("label")),
        "fear_greed_date": as_text(fear.get("data_date")),
        "phase": as_text(dig(evidence, "sentiment_regime", "altseason.phase")) or as_text(dig(data, "phase")),
        "material_shift": fear.get("material_shift"),
        "fear_greed_7d_ago": as_number(fear.get("baseline_7d_value")),
        "fear_greed_7d_ago_date": as_text(fear.get("baseline_7d_date")),
        "fear_greed_delta": change_pts,
        "fear_greed_direction": as_text(fear.get("change_direction")),
        "funding": {
            "data_date": as_text(fund.get("data_date")),
            "latest_bps": as_number(fund.get("latest_bps")),
            "mean_7d_bps": as_number(current_win.get("mean_bps")),
            "mean_7d_start": as_text(current_win.get("start_date")),
            "mean_7d_end": as_text(current_win.get("end_date")),
            "previous_7d_bps": as_number(previous_win.get("mean_bps")),
            "previous_7d_start": as_text(previous_win.get("start_date")),
            "previous_7d_end": as_text(previous_win.get("end_date")),
            "wow_change_bps": as_number(fund.get("wow_change_bps")),
            "wow_pct": as_number(fund.get("wow_change_pct")),
            "percentile_90d": as_number(fund.get("current_7d_percentile_90d")),
            "crowding": as_text(fund.get("crowding_state")),
        },
        "liquidation": {
            "data_date": as_text(liq.get("data_date")),
            "total_usd": as_number(liq.get("total_usd")),
            "dominant": as_text(liq.get("dominant_liquidated_side")),
            "long_share_pct": as_number(liq.get("long_share_pct")),
            "pressure": as_text(liq.get("pressure_state")),
            "percentile_90d": as_number(liq.get("percentile_90d")),
            "scope": as_text(liq.get("coverage_scope")),
        },
        "altseason": {
            "data_date": as_text(alt.get("data_date")),
            "index": as_number(alt.get("index")),
            "phase": as_text(alt.get("phase")),
        },
        "regime": as_text(evidence.get("sentiment_regime")),
        "source_attribution": as_text(data.get("source_attribution")),
        "warnings": warnings_of(envelope),
        "stale": bool((envelope or {}).get("stale")),
    }


def extract_token(envelope: dict[str, Any] | None, fallback_symbol: str | None = None) -> dict[str, Any]:
    data = data_of(envelope)
    summary = summary_of(envelope)
    result = result_of(envelope) or {}
    symbol = extract_symbol(data) or extract_symbol(result.get("request")) or (fallback_symbol.upper() if fallback_symbol else None)
    market = data.get("market") if isinstance(data.get("market"), dict) else {}
    tech = (
        data.get("technical_analysis")
        if isinstance(data.get("technical_analysis"), dict)
        else data.get("technicals")
        if isinstance(data.get("technicals"), dict)
        else data.get("technical")
        if isinstance(data.get("technical"), dict)
        else {}
    )
    perf = data.get("performance") if isinstance(data.get("performance"), dict) else {}
    verdict_raw = dig(data, "verdict", "intelligence.verdict", "market_intelligence.verdict", "bias")
    price = as_number(dig(market, "price_usd", "price", "usd", "last", "close")) or as_number(dig(data, "price_usd", "price"))
    change_1h = as_number(dig(perf, "change_1h_pct", "h1", "1h", "change_1h"))
    change_24h = as_number(dig(perf, "change_24h_pct", "h24", "24h", "change_24h"))
    change_7d = as_number(dig(perf, "change_7d_pct", "d7", "7d", "change_7d"))
    change_30d = as_number(dig(perf, "change_30d_pct", "d30", "30d", "change_30d", "momentum_30d_pct")) or as_number(dig(tech, "momentum_30d_pct"))
    rsi_14 = as_number(dig(tech, "rsi_14", "rsi"))
    atr_14_pct = as_number(dig(tech, "atr_14_pct", "atr_pct"))
    atr_14 = as_number(dig(tech, "atr_14", "atr"))
    if atr_14 is None and price is not None and atr_14_pct is not None:
        atr_14 = price * (atr_14_pct / 100.0)
    volume = as_number(dig(market, "volume_24h_usd", "volume", "volume_24h"))
    trend = as_text(dig(tech, "trend"))
    verdict = as_text(verdict_raw) if not isinstance(verdict_raw, dict) else as_text(dig(verdict_raw, "call", "label", "bias", "side", "text"))
    asset = data.get("asset") if isinstance(data.get("asset"), dict) else {}
    name = as_text(asset.get("name")) or as_text(dig(data, "name"))
    mcap = as_number(dig(market, "market_cap_usd", "mcap_usd"))
    fdv = as_number(dig(market, "fully_diluted_value_usd", "fdv_usd"))
    intel = data.get("intelligence") if isinstance(data.get("intelligence"), dict) else {}
    turnover = (volume / mcap) if volume is not None and mcap not in (None, 0) else None
    dilution = ((fdv / mcap) - 1.0) if fdv is not None and mcap not in (None, 0) else None
    measured = {
        "name": name,
        "rank": as_number(asset.get("rank")) or as_number(dig(data, "asset.rank")),
        "chain": as_text(asset.get("chain")),
        "contract": as_text(asset.get("contract")),
        "price": price,
        "change_1h": change_1h,
        "change_24h": change_24h,
        "change_7d": change_7d,
        "change_30d": change_30d,
        "momentum_30d": as_number(dig(tech, "momentum_30d_pct")),
        "mcap": mcap,
        "fdv": fdv,
        "turnover": turnover,
        "dilution": dilution,
        "narrative": as_text(intel.get("narrative")),
        "catalysts": intel.get("catalysts") if isinstance(intel.get("catalysts"), list) else [],
        "risks": intel.get("risks") if isinstance(intel.get("risks"), list) else [],
        "rsi_14": rsi_14,
        "atr_14": atr_14,
        "atr_14_pct": atr_14_pct,
        "volume": volume,
        "trend": trend,
        "verdict": verdict,
    }
    return {
        "symbol": symbol,
        "status": status_of(envelope),
        "data_mode": data_mode_of(envelope),
        "as_of": dig(result, "as_of"),
        "headline": as_text(summary.get("headline")) if summary else None,
        "points": flatten_points(summary.get("key_points") or summary.get("points")),
        **measured,
        "warnings": warnings_of(envelope),
        "stale": bool((envelope or {}).get("stale")),
        "available_fields": sorted(k for k, v in measured.items() if v is not None),
    }


def extract_scan_meta(envelope: dict[str, Any] | None) -> dict[str, Any]:
    data = data_of(envelope)
    summary = summary_of(envelope)
    result = result_of(envelope) or {}
    filters = data.get("filters") if isinstance(data.get("filters"), dict) else {}
    return {
        "status": status_of(envelope),
        "data_mode": data_mode_of(envelope),
        "as_of": dig(result, "as_of"),
        "headline": as_text(summary.get("headline")) if summary else None,
        "points": flatten_points(summary.get("key_points") or summary.get("points")),
        "selection_method": as_text(data.get("selection_method")),
        "candidate_count": as_number(data.get("candidate_count")),
        "excluded_candidate_count": as_number(data.get("excluded_candidate_count")),
        "filters": filters or None,
        "warnings": warnings_of(envelope),
        "stale": bool((envelope or {}).get("stale")),
    }


def extract_deep(envelope: dict[str, Any] | None, symbol: str | None = None) -> dict[str, Any]:
    data = data_of(envelope)
    summary = summary_of(envelope)
    result = result_of(envelope) or {}
    intel = data.get("intelligence") if isinstance(data.get("intelligence"), dict) else {}
    plan = dig(data, "trade_plan", "plan", "preview_plan", "atr_plan")
    verdict_raw = data.get("verdict")
    verdict = as_text(verdict_raw) if not isinstance(verdict_raw, dict) else as_text(dig(verdict_raw, "call", "headline"))
    confluence = data.get("confluence") if isinstance(data.get("confluence"), dict) else {}
    market = data.get("market") if isinstance(data.get("market"), dict) else {}
    asset = data.get("asset") if isinstance(data.get("asset"), dict) else {}
    tech = data.get("technical_analysis") if isinstance(data.get("technical_analysis"), dict) else {}
    perf = data.get("performance") if isinstance(data.get("performance"), dict) else {}
    return {
        "symbol": symbol or as_text(asset.get("symbol")),
        "status": status_of(envelope),
        "data_mode": data_mode_of(envelope),
        "as_of": dig(result, "as_of"),
        "headline": as_text(summary.get("headline")) if summary else None,
        "points": flatten_points(summary.get("key_points") or summary.get("points")),
        "catalysts": intel.get("catalysts") or data.get("catalysts"),
        "confluence_state": as_text(confluence.get("state")),
        "confluence_score": as_number(confluence.get("score")),
        "gates": confluence.get("gates") if isinstance(confluence.get("gates"), list) else [],
        "call": as_text(dig(verdict_raw, "call")) if isinstance(verdict_raw, dict) else verdict,
        "key_driver": as_text(dig(verdict_raw, "key_driver", "bottom_line")) if isinstance(verdict_raw, dict) else None,
        "bottom_line": as_text(dig(verdict_raw, "bottom_line")) if isinstance(verdict_raw, dict) else None,
        "what_changes_it": as_text(dig(verdict_raw, "what_changes_it")) if isinstance(verdict_raw, dict) else None,
        "risks": intel.get("risks") or data.get("risks"),
        "narrative": as_text(intel.get("narrative")),
        "confluence": data.get("confluence"),
        "verdict": verdict,
        "plan": plan,
        "preview_only": bool(plan.get("preview_only")) if isinstance(plan, dict) and "preview_only" in plan else None,
        "derivatives": data.get("derivatives"),
        "token_profile": data.get("token_profile"),
        "availability": result.get("availability") if isinstance(result.get("availability"), dict) else None,
        "market": {
            "price": as_number(market.get("price_usd")),
            "mcap": as_number(market.get("mcap_usd")),
            "fdv": as_number(market.get("fdv_usd")),
            "volume": as_number(market.get("volume_24h_usd")),
            "dominance_pct": as_number(market.get("dominance_pct")),
            "circulating_supply": as_number(market.get("circulating_supply")),
            "max_supply": as_number(market.get("max_supply")),
        },
        "performance": perf or None,
        "technicals": tech or None,
        "asset": asset or None,
        "warnings": warnings_of(envelope),
        "stale": bool((envelope or {}).get("stale")),
        "data_keys": sorted(data.keys()) if data else [],
    }


def flatten_points(value: Any) -> list[str]:
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            if isinstance(item, str) and item.strip():
                out.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text") or item.get("point") or item.get("message")
                if text:
                    out.append(str(text))
        return out
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
