from __future__ import annotations

import re
from typing import Any

PAIR_SUFFIXES = ("USDT", "USDC", "BUSD", "PERP")
SHAPE = re.compile(r"^[A-Z][A-Z0-9]{1,11}$")


def parse_symbol(raw: str | None) -> dict[str, Any]:
    """Shape only. No market call."""
    if raw is None:
        return {"ok": True, "symbol": None, "empty": True}
    text = str(raw).strip().upper()
    if not text:
        return {"ok": True, "symbol": None, "empty": True}
    text = text.replace("$", "")
    text = re.sub(r"\s+", "", text)
    text = text.replace("-", "/").replace("_", "/")
    if "/" in text:
        text = text.split("/", 1)[0]
    else:
        for suffix in PAIR_SUFFIXES:
            if len(text) > len(suffix) + 1 and text.endswith(suffix):
                text = text[: -len(suffix)]
                break
    if not SHAPE.match(text):
        return {
            "ok": False,
            "symbol": text or None,
            "empty": False,
            "error": "Use a ticker like SOL or BTC — letters and numbers only, 2 to 12 characters.",
            "code": "bad_shape",
        }
    return {"ok": True, "symbol": text, "empty": False}
