"""Small RYO-shaped replies for page tests. Numbers follow a real 2026-09-21 snapshot."""
import copy
import time

import pytest

OVERVIEW = {
    "status": "ok",
    "data_mode": "live",
    "as_of": "2026-09-21T11:07:48Z",
    "summary": {"headline": "Market regime: risk on."},
    "data": {
        "regime": "risk_on",
        "sentiment": {"fear_greed_index": 76.0, "label": "extreme_greed"},
        "market": {
            "total_market_cap_usd": 2879393693029.19,
            "total_volume_24h_usd": 104954993939.01,
            "market_cap_change_24h_pct": 5.08,
            "btc_dominance_pct": 58.96,
            "eth_dominance_pct": 11.52,
            "breadth": 0.913,
            "breadth_details": {"universe_size": 92, "advancing": 84, "declining": 8, "unchanged": 0},
        },
        "top_movers": {
            "gainers": [{"symbol": s, "name": s, "change_24h_pct": c} for s, c in [("SEI", 36.0), ("SUI", 23.7), ("NEAR", 18.5), ("VVV", 18.3), ("RENDER", 17.5)]],
            "losers": [{"symbol": s, "name": s, "change_24h_pct": c} for s, c in [("JST", -1.4), ("FF", -1.2), ("XAUT", -0.5), ("LEO", -0.5), ("PAXG", -0.4)]],
        },
    },
}

SENTIMENT = {
    "status": "ok",
    "data_mode": "live",
    "as_of": "2026-09-21T11:07:51Z",
    "data": {
        "summary": "Fear & Greed is 76 ... with no funding crowding signal.",
        "evidence": {
            "fear_greed": {"value": 76, "label": "extreme_greed", "baseline_7d_value": 69, "change_7d_points": 7, "change_direction": "up", "material_shift": False},
            "funding": {
                "latest_bps": 0.7086,
                "current_7d_window": {"mean_bps": 0.6886},
                "previous_7d_window": {"mean_bps": 0.4867},
                "wow_change_pct": 41.5,
                "current_7d_percentile_90d": 84.4,
                "crowding_state": "normal",
            },
            "liquidation": {"total_usd": 34789750.71, "dominant_liquidated_side": "longs", "percentile_90d": 43.3, "pressure_state": "normal", "long_share_pct": 64.3},
            "altseason": {"index": 50, "phase": "transition"},
            "sentiment_regime": "extreme_greed_unconfirmed",
        },
    },
}

SCAN = {
    "status": "ok",
    "data_mode": "live",
    "as_of": "2026-09-21T11:07:51Z",
    "data": {
        "candidates": [
            {"rank": 1, "symbol": "ZETA", "name": "ZetaChain", "price_usd": 0.0647, "change_24h_pct": 71.44, "market_cap_usd": 103956260, "volume_24h_usd": 128984758, "turnover_ratio": 1.24},
            {"rank": 2, "symbol": "NEAR", "name": "NEAR Protocol", "price_usd": 4.24, "change_24h_pct": 18.53, "market_cap_usd": 5537748912, "volume_24h_usd": 2277739165, "turnover_ratio": 0.41},
        ]
    },
}

BTC = {
    "status": "ok",
    "data_mode": "live",
    "as_of": "2026-09-21T11:07:52Z",
    "data": {
        "asset": {"symbol": "BTC", "name": "Bitcoin", "rank": 1},
        "market": {"price_usd": 84513.47, "market_cap_usd": 1697655777823.91, "volume_24h_usd": 36674171474.61},
        "performance": {"change_24h_pct": 5.2, "change_7d_pct": 8.8, "change_30d_pct": 9.76},
        "technical_analysis": {"trend": "up", "rsi_14": 66.1, "atr_14_pct": 2.73},
        "verdict": "accumulate",
    },
}

DOWN = {"status": "unavailable", "data_mode": "unknown", "summary": {"headline": "The research provider reported that this analysis is unavailable."}, "data": {}}

BY_TOOL = {"market_overview": OVERVIEW, "monitor_market_sentiment_shift": SENTIMENT, "scan_market": SCAN, "analyze_token": BTC, "deep_analysis": BTC}


def envelope(result, **extra):
    return {"ok": True, "stale": False, "fetched_at": time.time(), "result": copy.deepcopy(result), **extra}


@pytest.fixture
def ryo_replies(monkeypatch):
    """Route ryo.call_tool to canned replies. Call with a dict tool -> envelope (or result)."""
    from app import config, ryo, services

    monkeypatch.setattr(config, "ryo_configured", lambda: True)
    monkeypatch.setattr(config, "truenorth_configured", lambda: False)
    monkeypatch.setattr(ryo, "http", lambda: None)

    def install(overrides=None):
        table = {k: envelope(v) for k, v in BY_TOOL.items()}
        for tool, value in (overrides or {}).items():
            table[tool] = value if "result" in value else envelope(value)

        async def fake(_client, tool, _args=None, **_kw):
            return copy.deepcopy(table[tool])

        monkeypatch.setattr(ryo, "call_tool", fake)
        monkeypatch.setattr(services.ryo, "call_tool", fake)

    return install


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app import main

    return TestClient(main.app)
