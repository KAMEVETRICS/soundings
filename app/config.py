from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PARENT = ROOT.parent
load_dotenv(PARENT / ".env")
load_dotenv(ROOT / ".env", override=True)

DATA_DIR = ROOT / "data"
CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
RECEIPT_DIR = DATA_DIR / "receipts"
RECEIPT_DIR.mkdir(parents=True, exist_ok=True)

RYO_MCP_URL = os.getenv("RYO_MCP_URL", "https://app-ryochan.com/api/mcp").rstrip("/")
RYO_MCP_KEY = os.getenv("RYO_MCP_KEY", "").strip()
RYO_CACHE_TTL = float(os.getenv("RYO_CACHE_TTL", "180"))
RYO_SWR_TTL = float(os.getenv("RYO_SWR_TTL", "900"))
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip().rstrip("/")
XAI_API_KEY = os.getenv("XAI_API_KEY", "").strip()
TRUENORTH_MCP_URL = os.getenv("TRUENORTH_MCP_URL", "").strip()
TRUENORTH_MCP_TOKEN = os.getenv("TRUENORTH_MCP_TOKEN", "").strip()


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
