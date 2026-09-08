from __future__ import annotations

import asyncio
import hashlib
import json
import random
import time
from typing import Any

import httpx

from . import config
from .store import cache_get, cache_put

RETRY_STATUSES = {429, 503, 502, 504}
MAX_ATTEMPTS = 4


class RyoError(Exception):
    def __init__(self, message: str, *, status: int | None = None, code: str | None = None, trace: str | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.trace = trace


def _headers() -> dict[str, str]:
    if not config.RYO_MCP_KEY:
        raise RyoError("RYO_MCP_KEY is not set", code="missing_key")
    return {
        "Authorization": f"Bearer {config.RYO_MCP_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _cache_key(tool: str, arguments: dict[str, Any] | None) -> str:
    payload = json.dumps({"tool": tool, "arguments": arguments or {}}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


async def _request(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    *,
    json_body: dict[str, Any] | None = None,
    auth: bool = True,
) -> tuple[dict[str, Any], dict[str, str]]:
    url = f"{config.RYO_MCP_URL}{path}"
    headers = _headers() if auth else {"Accept": "application/json"}
    last_exc: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = await client.request(method, url, headers=headers, json=json_body, timeout=60.0)
        except httpx.HTTPError as exc:
            last_exc = exc
            if attempt == MAX_ATTEMPTS - 1:
                raise RyoError(f"network error: {exc}", code="network") from exc
            await asyncio.sleep((2**attempt) + random.random())
            continue

        hdrs = {k.lower(): v for k, v in response.headers.items()}
        if response.status_code in RETRY_STATUSES:
            retry_after = hdrs.get("retry-after")
            wait = float(retry_after) if retry_after and retry_after.replace(".", "", 1).isdigit() else (2**attempt) + random.random()
            if attempt == MAX_ATTEMPTS - 1:
                raise RyoError(
                    f"rate limited or unavailable ({response.status_code})",
                    status=response.status_code,
                    code="retry_exhausted",
                    trace=hdrs.get("x-trace-id") or hdrs.get("x-request-id"),
                )
            await asyncio.sleep(wait)
            continue

        if response.status_code >= 400:
            try:
                body = response.json()
            except Exception:
                body = {"message": response.text[:500]}
            raise RyoError(
                str(body.get("message") or body.get("error") or f"HTTP {response.status_code}"),
                status=response.status_code,
                code=str(body.get("code") or "http_error"),
                trace=str(body.get("trace") or body.get("trace_id") or ""),
            )

        try:
            data = response.json()
        except Exception as exc:
            raise RyoError("RYO returned non-JSON", code="bad_json") from exc
        if isinstance(data, list) and path.rstrip("/").endswith("/tools"):
            return {"tools": data}, hdrs
        if not isinstance(data, dict):
            raise RyoError("RYO returned a non-object JSON payload", code="bad_json")
        return data, hdrs

    raise RyoError(f"request failed: {last_exc}", code="network")


async def health(client: httpx.AsyncClient) -> dict[str, Any]:
    data, _ = await _request(client, "GET", "/health", auth=False)
    return data


async def whoami(client: httpx.AsyncClient) -> dict[str, Any]:
    data, _ = await _request(client, "GET", "/whoami")
    return data


async def catalog(client: httpx.AsyncClient) -> dict[str, Any]:
    data, _ = await _request(client, "GET", "/tools")
    return data


async def call_tool(
    client: httpx.AsyncClient,
    tool: str,
    arguments: dict[str, Any] | None = None,
    *,
    allow_stale: bool = True,
) -> dict[str, Any]:
    """Call a RYO tool. Fresh hits reuse disk cache for RYO_CACHE_TTL seconds. On failure, last-good is tagged stale."""
    arguments = arguments or {}
    key = _cache_key(tool, arguments)
    cached = cache_get(key)
    if cached and cached.get("ok") and not cached.get("stale"):
        try:
            age = time.time() - float(cached.get("fetched_at") or 0)
        except (TypeError, ValueError):
            age = config.RYO_CACHE_TTL + 1
        if age < config.RYO_CACHE_TTL:
            return cached
    try:
        payload, hdrs = await _request(client, "POST", f"/tools/{tool}/call", json_body=arguments)
        result = payload.get("result", payload)
        if not isinstance(result, dict):
            raise RyoError("tool result was not an object", code="bad_shape")
        envelope = {
            "ok": True,
            "stale": False,
            "tool": tool,
            "arguments": arguments,
            "fetched_at": time.time(),
            "rate_limit": {
                "limit": hdrs.get("x-ratelimit-limit"),
                "remaining": hdrs.get("x-ratelimit-remaining"),
                "reset": hdrs.get("x-ratelimit-reset"),
            },
            "result": result,
        }
        cache_put(key, envelope)
        return envelope
    except RyoError as exc:
        cached = cache_get(key) if allow_stale else None
        if cached:
            return {
                **cached,
                "ok": False,
                "stale": True,
                "error": {"message": str(exc), "code": exc.code, "status": exc.status, "trace": exc.trace},
            }
        return {
            "ok": False,
            "stale": False,
            "tool": tool,
            "arguments": arguments,
            "fetched_at": time.time(),
            "error": {"message": str(exc), "code": exc.code, "status": exc.status, "trace": exc.trace},
            "result": None,
        }
