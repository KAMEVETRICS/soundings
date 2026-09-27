import asyncio

from app import config, ryo, services
from app.services import _annotate_heat


UNAVAILABLE_SCAN = {
    "ok": True,
    "stale": False,
    "tool": "scan_market",
    "result": {
        "tool": "scan_market",
        "status": "unavailable",
        "data_mode": "unknown",
        "summary": {"headline": "The research provider reported that this analysis is unavailable."},
        "data": {},
    },
}


def test_annotate_heat_empty_rows():
    assert _annotate_heat([]) == []


def test_annotate_heat_rows_without_volume():
    rows = _annotate_heat([{"symbol": "AAA", "volume": None, "change_24h": None}])
    assert rows[0]["heat"] == "flat"
    assert rows[0]["heat_flex"] == 1.0


def test_load_screener_survives_empty_scan(monkeypatch):
    async def fake_call_tool(_client, _name, _args):
        return UNAVAILABLE_SCAN

    monkeypatch.setattr(config, "ryo_configured", lambda: True)
    monkeypatch.setattr(ryo, "http", lambda: None)
    monkeypatch.setattr(ryo, "call_tool", fake_call_tool)

    data = asyncio.run(services.load_screener(top_n=8))
    assert data["ok"] is True
    assert data["rows"] == []
    assert data["spikes"] == []
    assert data["scan_volume"] == 0
    assert data["top_gainer"] is None
    assert data["top_loser"] is None
