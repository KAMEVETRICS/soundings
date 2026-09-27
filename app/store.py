from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from . import config

PRUNE_EVERY = 100  # puts between sweeps of old cache files
_puts = 0


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def cache_put(key: str, payload: dict[str, Any]) -> None:
    """Write to a temp file, then rename: a crash or a concurrent write never leaves half a file."""
    global _puts
    path = config.CACHE_DIR / f"{key}.json"
    tmp = path.with_name(f".{key}.{uuid.uuid4().hex[:8]}.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    _puts += 1
    if _puts % PRUNE_EVERY == 0:
        prune_cache()


def cache_get(key: str) -> dict[str, Any] | None:
    return _read_json(config.CACHE_DIR / f"{key}.json")


def prune_cache(max_age: float | None = None) -> int:
    """Delete cache files (and stray temp files) older than max_age. Keeps the folder bounded."""
    max_age = config.CACHE_MAX_AGE if max_age is None else max_age
    cutoff = time.time() - max_age
    removed = 0
    for path in list(config.CACHE_DIR.glob("*.json")) + list(config.CACHE_DIR.glob(".*.tmp")):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
        except OSError:
            pass
    return removed
