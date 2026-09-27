from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
_OWN_ENV = ROOT / ".env"
_PARENT_ENV = ROOT.parent / ".env"
if _OWN_ENV.exists():
    load_dotenv(_OWN_ENV)
elif _PARENT_ENV.exists():
    # Older layouts kept .env one folder up. Still supported, but never mixed with a local .env.
    print(f"[soundings] no {_OWN_ENV}; using {_PARENT_ENV}. Move it into the app folder.", flush=True)
    load_dotenv(_PARENT_ENV)

DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

RYO_MCP_URL = os.getenv("RYO_MCP_URL", "https://app-ryochan.com/api/mcp").rstrip("/")
RYO_MCP_KEY = os.getenv("RYO_MCP_KEY", "").strip()
RYO_CACHE_TTL = float(os.getenv("RYO_CACHE_TTL", "180"))
RYO_SWR_TTL = float(os.getenv("RYO_SWR_TTL", "900"))
# How old last-good data may be and still stand in for a failed or degraded RYO reply.
RYO_LASTGOOD_TTL = float(os.getenv("RYO_LASTGOOD_TTL", "172800"))
# Cache files older than this are deleted. Must exceed RYO_LASTGOOD_TTL.
CACHE_MAX_AGE = max(float(os.getenv("CACHE_MAX_AGE", "604800")), RYO_LASTGOOD_TTL)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip().rstrip("/")
XAI_API_KEY = os.getenv("XAI_API_KEY", "").strip()
TRUENORTH_MCP_URL = os.getenv("TRUENORTH_MCP_URL", "").strip()
TRUENORTH_MCP_TOKEN = os.getenv("TRUENORTH_MCP_TOKEN", "").strip()

# Public endpoints share one RYO key (60 calls/min) and one paid LLM key.
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "120"))  # any page or API call, per IP
TOKEN_LIMIT_PER_MIN = int(os.getenv("TOKEN_LIMIT_PER_MIN", "12"))  # /token and /api/token, per IP
CLAW_LIMIT_PER_MIN = int(os.getenv("CLAW_LIMIT_PER_MIN", "4"))  # /api/claw, per IP
CLAW_DAILY_LIMIT = int(os.getenv("CLAW_DAILY_LIMIT", "300"))  # /api/claw, whole site, per UTC day
UNKNOWN_TICKER_TTL = float(os.getenv("UNKNOWN_TICKER_TTL", "3600"))  # remember misses; don't re-ask RYO


def ryo_configured() -> bool:
    return bool(RYO_MCP_KEY)


def truenorth_configured() -> bool:
    return bool(TRUENORTH_MCP_URL and TRUENORTH_MCP_TOKEN)


def llm_provider() -> str | None:
    if OPENROUTER_API_KEY:
        return "openrouter"
    if XAI_API_KEY:
        return "xai"
    return None


def llm_configured() -> bool:
    return llm_provider() is not None


_OPENROUTER_ALIASES = {
    "grok-4.6": "x-ai/grok-4.3",
    "grok-4.5": "x-ai/grok-4.3",
    "grok-4": "x-ai/grok-4.3",
}


def chamber_model() -> str:
    explicit = os.getenv("CHAMBER_MODEL", "").strip()
    provider = llm_provider()
    if explicit:
        if provider == "openrouter" and "/" not in explicit:
            return _OPENROUTER_ALIASES.get(explicit, "x-ai/grok-4.3")
        return explicit
    return "x-ai/grok-4.3" if provider == "openrouter" else "grok-4.6"
