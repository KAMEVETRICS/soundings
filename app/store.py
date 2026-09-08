from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from . import config


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def cache_put(key: str, payload: dict[str, Any]) -> None:
    path = config.CACHE_DIR / f"{key}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def cache_get(key: str) -> dict[str, Any] | None:
    return _read_json(config.CACHE_DIR / f"{key}.json")


def save_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    receipt_id = receipt.get("id") or uuid.uuid4().hex[:12]
    receipt["id"] = receipt_id
    receipt["saved_at"] = receipt.get("saved_at") or time.time()
    path = config.RECEIPT_DIR / f"{receipt_id}.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    return receipt


def load_receipt(receipt_id: str) -> dict[str, Any] | None:
    safe = "".join(ch for ch in receipt_id if ch.isalnum() or ch in "-_")
    if not safe:
        return None
    return _read_json(config.RECEIPT_DIR / f"{safe}.json")


def list_receipts(limit: int = 20) -> list[dict[str, Any]]:
    files = sorted(config.RECEIPT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    out: list[dict[str, Any]] = []
    for path in files[:limit]:
        data = _read_json(path)
        if not data:
            continue
        out.append(
            {
                "id": data.get("id") or path.stem,
                "as_of": data.get("as_of"),
                "saved_at": data.get("saved_at"),
                "symbol": data.get("ticket", {}).get("symbol") or data.get("winner", {}).get("symbol"),
                "ruling": data.get("ticket", {}).get("side") or data.get("chair", {}).get("ruling"),
                "headline": data.get("headline"),
                "stale": data.get("stale"),
            }
        )
    return out
