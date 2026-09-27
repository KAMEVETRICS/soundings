import asyncio
import time

import pytest

from app import config, ryo, store

GOOD = {"status": "ok", "availability": {"a": "available", "b": "available", "c": "available"}, "data": {"x": 1}}
PARTIAL_THIN = {"status": "partial", "availability": {"a": "available", "b": "unavailable", "c": "unavailable"}, "data": {"x": 1}}
DOWN = {"status": "unavailable", "summary": {"headline": "The research provider reported that this analysis is unavailable."}, "data": {}}
ARGS = {"time_window": "7d"}
TOOL = "monitor_market_sentiment_shift"


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(config, "RYO_CACHE_TTL", 180.0)
    monkeypatch.setattr(config, "RYO_SWR_TTL", 900.0)
    monkeypatch.setattr(config, "RYO_LASTGOOD_TTL", 172800.0)
    ryo._MEM.clear()
    ryo._INFLIGHT.clear()
    yield
    ryo._MEM.clear()


def _key():
    return ryo._cache_key(TOOL, ARGS)


def _seed(result, age):
    store.cache_put(_key(), {"ok": True, "stale": False, "tool": TOOL, "arguments": ARGS, "fetched_at": time.time() - age, "result": result})


def _replies(monkeypatch, *results):
    calls = []

    async def fake(client, method, path, *, json_body=None, auth=True):
        calls.append(path)
        await asyncio.sleep(0.01)
        r = results[min(len(calls) - 1, len(results) - 1)]
        if isinstance(r, Exception):
            raise r
        return {"result": dict(r)}, {}

    monkeypatch.setattr(ryo, "_request", fake)
    return calls


def call():
    return asyncio.run(ryo.call_tool(None, TOOL, ARGS))


def test_unavailable_reply_keeps_last_good(monkeypatch):
    _seed(GOOD, age=10_000)  # past the SWR window, so a fetch happens
    _replies(monkeypatch, DOWN)
    env = call()
    assert env["result"]["status"] == "ok" and env["stale"] is True
    assert env["error"]["code"] == "upstream_degraded"
    assert store.cache_get(_key())["result"]["status"] == "ok"  # disk untouched


def test_unavailable_reply_without_cache_is_shown_but_not_cached(monkeypatch):
    _replies(monkeypatch, DOWN)
    env = call()
    assert env["result"]["status"] == "unavailable"
    assert store.cache_get(_key()) is None


def test_thin_partial_does_not_replace_full_data(monkeypatch):
    _seed(GOOD, age=10_000)
    _replies(monkeypatch, PARTIAL_THIN)
    env = call()
    assert env["stale"] is True and env["result"]["status"] == "ok"


def test_fresh_ok_reply_replaces_cache(monkeypatch):
    _seed(GOOD, age=10_000)
    newer = {**GOOD, "data": {"x": 2}}
    _replies(monkeypatch, newer)
    env = call()
    assert env["stale"] is False and env["result"]["data"]["x"] == 2
    assert store.cache_get(_key())["result"]["data"]["x"] == 2


def test_poisoned_cache_from_old_version_is_not_served_as_fresh(monkeypatch):
    _seed(DOWN, age=5)  # what the old code saved during the outage
    calls = _replies(monkeypatch, GOOD)
    env = call()
    assert calls, "should have fetched instead of serving the cached 'unavailable'"
    assert env["result"]["status"] == "ok"


def test_last_good_too_old_is_not_used(monkeypatch):
    _seed(GOOD, age=config.RYO_LASTGOOD_TTL + 60)
    _replies(monkeypatch, DOWN)
    assert call()["result"]["status"] == "unavailable"


def test_network_error_serves_last_good(monkeypatch):
    _seed(GOOD, age=10_000)
    _replies(monkeypatch, ryo.RyoError("boom", code="network"))
    env = call()
    assert env["stale"] is True and env["error"]["code"] == "network"


def test_concurrent_misses_share_one_request(monkeypatch):
    calls = _replies(monkeypatch, GOOD)

    async def many():
        return await asyncio.gather(*[ryo.call_tool(None, TOOL, ARGS) for _ in range(5)])

    results = asyncio.run(many())
    assert len(calls) == 1
    assert all(r["result"]["status"] == "ok" for r in results)


def test_cache_put_is_atomic_and_prunes(tmp_path):
    store.cache_put("k", {"a": 1})
    assert store.cache_get("k") == {"a": 1}
    assert not list(tmp_path.glob(".*.tmp"))
    old = tmp_path / "old.json"
    old.write_text("{}")
    past = time.time() - 10 * 86400
    import os

    os.utime(old, (past, past))
    assert store.prune_cache(max_age=7 * 86400) == 1
    assert not old.exists() and (tmp_path / "k.json").exists()
