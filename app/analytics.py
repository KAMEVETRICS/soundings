from __future__ import annotations

from typing import Any

from .extract import as_number


def _clip(value: float, lo: float = -3.0, hi: float = 3.0) -> float:
    return max(lo, min(hi, value))


def z_from_center(value: Any, center: float = 50.0, scale: float = 25.0) -> float | None:
    """Map a 0–100 reading onto a z-like unit. Live approximation, not a rolling z-score."""
    number = as_number(value)
    if number is None or scale == 0:
        return None
    return _clip((number - center) / scale)


def _reading(score: float | None) -> str:
    if score is None:
        return "unavailable"
    if score >= 0.8:
        return "extreme froth"
    if score >= 0.4:
        return "froth"
    if score <= -0.8:
        return "extreme capitulation"
    if score <= -0.4:
        return "capitulation"
    return "neutral"


def _crowd_label(fear_greed: float | None, label: str | None) -> str:
    if fear_greed is None:
        return (label or "unknown").lower()
    if fear_greed >= 70:
        return "greed"
    if fear_greed <= 30:
        return "fear"
    return "neutral"


def _tape_label(crowding: str | None, percentile: float | None) -> str:
    state = (crowding or "").lower()
    if state == "crowded" or (percentile is not None and percentile >= 70):
        return "crowded"
    if state in {"uncrowded", "light"} or (percentile is not None and percentile <= 30):
        return "uncrowded"
    if state:
        return state
    if percentile is None:
        return "unknown"
    return "normal"


def _gap(crowd: str, tape: str) -> dict[str, str]:
    """Surface Fear & Greed versus BTC funding underneath."""
    if crowd == "greed" and tape in {"normal", "uncrowded"}:
        return {"code": "crowd_hotter_than_tape", "label": "Crowd hotter than tape", "body": "Greedy crowd, funding not crowded."}
    if crowd == "greed" and tape == "crowded":
        return {"code": "aligned_froth", "label": "Aligned froth", "body": "Greedy crowd, crowded funding."}
    if crowd == "fear" and tape == "crowded":
        return {"code": "tape_hotter_than_crowd", "label": "Tape hotter than crowd", "body": "Fearful crowd, funding still crowded."}
    if crowd == "fear" and tape == "uncrowded":
        return {"code": "aligned_fear", "label": "Aligned fear", "body": "Fearful crowd, light funding."}
    if crowd == "fear" and tape == "normal":
        return {"code": "crowd_colder_than_tape", "label": "Crowd colder than tape", "body": "Fearful crowd, normal funding."}
    if crowd == "greed":
        return {"code": "crowd_hot", "label": "Crowd hot", "body": "Greedy crowd."}
    return {"code": "aligned_neutral", "label": "Mid-range", "body": "Crowd and funding mid-range."}


def positioning_stress(
    overview: dict[str, Any] | None,
    sentiment: dict[str, Any] | None,
    btc: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Live positioning-stress pack from this RYO snapshot.

    Weights: 0.5 Fear & Greed, 0.5 funding, 0 stretch. Not a rolling z, not a trade, not OI.
    """
    overview = overview or {}
    sentiment = sentiment or {}
    funding = sentiment.get("funding") if isinstance(sentiment.get("funding"), dict) else {}
    liquidation = sentiment.get("liquidation") if isinstance(sentiment.get("liquidation"), dict) else {}
    altseason = sentiment.get("altseason") if isinstance(sentiment.get("altseason"), dict) else {}
    btc = btc or {}

    fg = as_number(sentiment.get("fear_greed"))
    if fg is None:
        fg = as_number(overview.get("fear_greed"))
    fg_label = sentiment.get("fear_greed_label") or overview.get("fear_greed_label")
    fund_pctl = as_number(funding.get("percentile_90d"))
    liq_pctl = as_number(liquidation.get("percentile_90d"))
    rsi = as_number(btc.get("rsi_14"))

    z_fng = z_from_center(fg)
    z_funding = z_from_center(fund_pctl)
    z_stretch = z_from_center(rsi)
    z_liq = z_from_center(liq_pctl)

    weights = {"w_fng": 0.5, "w_funding": 0.5, "w_stretch": 0.0}
    used: list[tuple[str, float, float]] = []
    if z_fng is not None:
        used.append(("fng", weights["w_fng"], z_fng))
    if z_funding is not None:
        used.append(("funding", weights["w_funding"], z_funding))
    total_w = sum(item[1] for item in used)
    score = sum(item[1] * item[2] for item in used) / total_w if total_w else None

    crowd = _crowd_label(fg, fg_label if isinstance(fg_label, str) else None)
    tape = _tape_label(funding.get("crowding") if isinstance(funding.get("crowding"), str) else None, fund_pctl)
    gap = _gap(crowd, tape)

    needle = None
    if score is not None:
        needle = max(0.0, min(100.0, ((score + 2.0) / 4.0) * 100.0))

    components = [
        {"key": "fear_greed", "label": "Crowd F&G", "raw": fg, "z": z_fng, "weight": weights["w_fng"], "in_s": z_fng is not None},
        {"key": "funding", "label": "Funding pctl", "raw": fund_pctl, "z": z_funding, "weight": weights["w_funding"], "in_s": z_funding is not None},
        {"key": "stretch", "label": "BTC RSI", "raw": rsi, "z": z_stretch, "weight": weights["w_stretch"], "in_s": False},
        {"key": "liquidations", "label": "Liq pctl", "raw": liq_pctl, "z": z_liq, "weight": 0.0, "in_s": False},
    ]
    for row in components:
        z = row["z"]
        row["bar"] = abs(z) * 25 if z is not None else 0
        row["side"] = "pos" if (z or 0) >= 0 else "neg"

    btc_dom = as_number(overview.get("btc_dominance"))
    eth_dom = as_number(overview.get("eth_dominance"))
    rest_dom = None
    if btc_dom is not None:
        rest_dom = 100.0 - btc_dom - (eth_dom or 0.0)
    liq_long = as_number(liquidation.get("long_share_pct"))
    adv = overview.get("advancing")
    dec = overview.get("declining")
    breadth_n = (adv or 0) + (dec or 0) if isinstance(adv, int) and isinstance(dec, int) else 0

    return {
        "S": score,
        "reading": _reading(score),
        "needle_pct": needle,
        "weights": weights,
        "components": components,
        "z": {"fng" : z_fng, "funding": z_funding, "stretch": z_stretch, "liquidations": z_liq},
        "crowd": {
            "label": crowd,
            "fear_greed": fg,
            "fear_greed_label": fg_label,
            "fear_greed_7d_ago": as_number(sentiment.get("fear_greed_7d_ago")),
            "fear_greed_delta": as_number(sentiment.get("fear_greed_delta")),
            "material_shift": sentiment.get("material_shift"),
            "shift": sentiment.get("shift"),
        },
        "tape": {
            "label": tape,
            "funding": funding,
            "liquidation": liquidation,
            "altseason": altseason,
            "sentiment_regime": sentiment.get("regime") or sentiment.get("phase"),
            "market_regime": overview.get("regime"),
            "btc_dominance": btc_dom,
            "eth_dominance": eth_dom,
            "rest_dominance": rest_dom,
            "breadth_ratio": as_number(overview.get("breadth_ratio")),
            "advancing": overview.get("advancing"),
            "declining": overview.get("declining"),
            "unchanged": overview.get("unchanged"),
            "mcap_change_24h": as_number(overview.get("mcap_change_24h")),
            "btc_trend": btc.get("trend"),
            "btc_rsi_14": rsi,
            "btc_change_30d": as_number(btc.get("change_30d")),
        },
        "gap": gap,
        "measurement": {"label": gap["label"], "code": gap["code"]},
        "viz": {
            "fg": fg,
            "fund_pctl": fund_pctl,
            "liq_long": liq_long,
            "liq_short": (100.0 - liq_long) if liq_long is not None else None,
            "btc_dom": btc_dom,
            "eth_dom": eth_dom,
            "rest_dom": rest_dom,
            "adv_pct": (100.0 * adv / breadth_n) if breadth_n else None,
            "dec_pct": (100.0 * dec / breadth_n) if breadth_n else None,
        },
    }
