"""Per-IP request limits for the public site. In-process, no extra dependency.

Everything shares one RYO key (60 calls/min) and one paid LLM key, so:
- /api/claw: a few per minute per IP, and a site-wide daily cap (each call is a paid LLM request).
- /token/* and /api/token/*: per IP and site-wide, since an unknown symbol costs two RYO calls.
- every other page or API call: a generous per-IP cap.

The client IP is request.client.host. Behind Caddy, uvicorn runs with --proxy-headers and
--forwarded-allow-ips=127.0.0.1, so that is the visitor's address, not the proxy's.
Limits are per process; the app runs one uvicorn process.
"""

from __future__ import annotations

import math
import time
from collections import deque
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

from . import config

WINDOW = 60.0
TOKEN_SITE_PER_MIN = 30  # all IPs together; keeps half the RYO key for everything else
SWEEP_EVERY = 500  # requests between clean-ups of idle IP entries


class SlidingWindow:
    """At most `limit` hits per `window` seconds for each key."""

    def __init__(self, limit: int, window: float = WINDOW):
        self.limit = limit
        self.window = window
        self.hits: dict[str, deque[float]] = {}

    def check(self, key: str, now: float) -> float:
        """Record a hit. Returns 0 if allowed, else seconds until the next hit is allowed."""
        q = self.hits.setdefault(key, deque())
        while q and q[0] <= now - self.window:
            q.popleft()
        if len(q) >= self.limit:
            if not q:  # limit 0: always blocked
                return self.window
            return max(0.0, q[0] + self.window - now)
        q.append(now)
        return 0.0

    def sweep(self, now: float) -> None:
        stale = [k for k, q in self.hits.items() if not q or q[-1] <= now - self.window]
        for k in stale:
            del self.hits[k]


class DailyCap:
    """At most `limit` hits per UTC day, site-wide."""

    def __init__(self, limit: int):
        self.limit = limit
        self.day = ""
        self.count = 0

    def check(self, now: float) -> float:
        day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
        if day != self.day:
            self.day, self.count = day, 0
        if self.count >= self.limit:
            midnight = datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() + 86400
            return max(1.0, midnight - now)
        self.count += 1
        return 0.0


class Limits:
    def __init__(self) -> None:
        self.general = SlidingWindow(config.RATE_LIMIT_PER_MIN)
        self.token = SlidingWindow(config.TOKEN_LIMIT_PER_MIN)
        self.token_site = SlidingWindow(TOKEN_SITE_PER_MIN)
        self.claw = SlidingWindow(config.CLAW_LIMIT_PER_MIN)
        self.claw_day = DailyCap(config.CLAW_DAILY_LIMIT)
        self._seen = 0

    def wait_for(self, method: str, path: str, ip: str, now: float) -> tuple[float, str]:
        """Seconds to wait (0 = allowed) and which limit applied."""
        self._seen += 1
        if self._seen % SWEEP_EVERY == 0:
            for window in (self.general, self.token, self.token_site, self.claw):
                window.sweep(now)
        if path.startswith("/static/"):
            return 0.0, ""
        if wait := self.general.check(ip, now):
            return wait, "requests"
        if method == "POST" and path.rstrip("/") == "/api/claw":
            if wait := self.claw.check(ip, now):
                return wait, "Claw questions"
            if wait := self.claw_day.check(now):
                return wait, "Claw questions today"
        if path.startswith("/token/") or path.startswith("/api/token/"):
            if wait := self.token.check(ip, now):
                return wait, "token lookups"
            if wait := self.token_site.check("*", now):
                return wait, "token lookups"
        return 0.0, ""


limits = Limits()


def _too_many(path: str, wait: float, what: str) -> Response:
    seconds = max(1, math.ceil(wait))
    message = f"Too many {what}. Try again in {seconds} s."
    headers = {"Retry-After": str(seconds)}
    if path.startswith("/api"):
        return JSONResponse({"ok": False, "error": message, "code": "rate_limited"}, status_code=429, headers=headers)
    body = f'<!doctype html><meta charset="utf-8"><title>Slow down</title><div id="main"><p class="banner warn">{message}</p></div>'
    return HTMLResponse(body, status_code=429, headers=headers)


async def rate_limit(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    wait, what = limits.wait_for(request.method, request.url.path, ip, time.time())
    if wait:
        return _too_many(request.url.path, wait, what)
    return await call_next(request)
