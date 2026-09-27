import asyncio

import pytest
from conftest import envelope

from app import config, limits, services
from app.limits import DailyCap, Limits, SlidingWindow


def test_sliding_window_blocks_then_frees():
    w = SlidingWindow(limit=2, window=60)
    assert w.check("ip", 0) == 0 and w.check("ip", 1) == 0
    assert w.check("ip", 2) == pytest.approx(58)  # third within a minute: wait until the first expires
    assert w.check("other", 2) == 0  # per key
    assert w.check("ip", 61) == 0


def test_daily_cap_resets_at_utc_midnight():
    cap = DailyCap(limit=1)
    day1 = 1_790_000_000.0
    assert cap.check(day1) == 0
    assert cap.check(day1 + 10) > 0
    assert cap.check(day1 + 86400) == 0


def test_claw_and_token_limits_are_separate_from_pages(monkeypatch):
    monkeypatch.setattr(config, "CLAW_LIMIT_PER_MIN", 2)
    monkeypatch.setattr(config, "TOKEN_LIMIT_PER_MIN", 3)
    lim = Limits()
    now = 1000.0
    assert [lim.wait_for("POST", "/api/claw", "a", now)[0] == 0 for _ in range(3)] == [True, True, False]
    assert lim.wait_for("GET", "/analytics", "a", now)[0] == 0  # pages still fine
    assert [lim.wait_for("GET", f"/token/X{i}", "b", now)[0] == 0 for i in range(4)] == [True, True, True, False]
    assert lim.wait_for("GET", "/static/styles.css", "b", now)[0] == 0


def test_site_wide_token_cap_across_ips():
    lim = Limits()
    allowed = sum(lim.wait_for("GET", "/api/token/AAA", f"ip{i}", 5.0)[0] == 0 for i in range(40))
    assert allowed == limits.TOKEN_SITE_PER_MIN


def test_429_shape_for_api_and_pages(ryo_replies, client, monkeypatch):
    ryo_replies()
    monkeypatch.setattr(limits, "limits", Limits())
    monkeypatch.setattr(limits.limits, "claw", SlidingWindow(limit=0))
    r = client.post("/api/claw", json={"question": "Is the crowd hotter than funding?"})
    assert r.status_code == 429 and r.json()["code"] == "rate_limited" and int(r.headers["Retry-After"]) >= 1
    monkeypatch.setattr(limits.limits, "general", SlidingWindow(limit=0))
    page = client.get("/analytics")
    assert page.status_code == 429 and 'id="main"' in page.text


def test_whoami_is_not_public(ryo_replies, client):
    ryo_replies()
    assert client.get("/api/whoami").status_code == 404
    assert "GET /api/whoami" not in client.get("/api").json()["endpoints"]


def test_unknown_ticker_is_remembered(ryo_replies, monkeypatch):
    services._UNKNOWN.clear()
    no_price = {"status": "ok", "data": {"asset": {"symbol": "ZZZZ"}, "market": {}}}
    ryo_replies({"analyze_token": no_price, "deep_analysis": no_price})
    calls = []
    real = services.ryo.call_tool

    async def counting(client, tool, args=None, **kw):
        calls.append(tool)
        return await real(client, tool, args, **kw)

    monkeypatch.setattr(services.ryo, "call_tool", counting)
    first = asyncio.run(services.load_token("ZZZZ"))
    second = asyncio.run(services.load_token("ZZZZ"))
    assert first["code"] == second["code"] == "unknown_ticker"
    assert calls.count("analyze_token") == 1  # second ask never reached RYO


def test_outage_is_not_remembered_as_unknown(ryo_replies):
    services._UNKNOWN.clear()
    from conftest import DOWN

    ryo_replies({"analyze_token": DOWN, "deep_analysis": DOWN})
    asyncio.run(services.load_token("BTC"))
    assert "BTC" not in services._UNKNOWN


def test_unknown_memory_is_bounded(monkeypatch):
    services._UNKNOWN.clear()
    monkeypatch.setattr(services, "_UNKNOWN_MAX", 10)
    for i in range(50):
        services._remember_unknown(f"S{i}")
    assert len(services._UNKNOWN) <= 10
