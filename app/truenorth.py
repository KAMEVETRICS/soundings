from __future__ import annotations

import json
from typing import Any

import httpx

from . import config


class TrueNorthError(Exception):
    pass


def _parse_sse(text: str) -> dict[str, Any]:
    for line in text.splitlines():
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    return json.loads(text)


def _unwrap(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("error"):
        raise TrueNorthError(str(payload["error"]))
    result = payload.get("result") or {}
    if result.get("isError"):
        raise TrueNorthError(str(result.get("content") or result))
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    for block in result.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
            try:
                parsed = json.loads(block["text"])
                return parsed if isinstance(parsed, dict) else {"value": parsed}
            except json.JSONDecodeError:
                return {"text": block["text"]}
    return result if isinstance(result, dict) else {"value": result}


class TrueNorth:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self._ready = False
        self._n = 0

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.TRUENORTH_MCP_TOKEN}",
        }

    async def _rpc(self, method: str, params: dict[str, Any] | None = None, *, notify: bool = False) -> dict[str, Any] | None:
        self._n += 1
        body: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if not notify:
            body["id"] = self._n
        if params is not None:
            body["params"] = params
        response = await self.client.post(
            config.TRUENORTH_MCP_URL,
            headers=self._headers(),
            json=body,
            timeout=45.0,
        )
        if notify:
            return None
        if response.status_code >= 400:
            raise TrueNorthError(f"HTTP {response.status_code}")
        return _unwrap(_parse_sse(response.text))

    async def ready(self) -> None:
        if self._ready:
            return
        await self._rpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "soundings", "version": "0.3"},
            },
        )
        await self._rpc("notifications/initialized", notify=True)
        self._ready = True

    async def call(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        await self.ready()
        return await self._rpc("tools/call", {"name": name, "arguments": arguments or {}}) or {}


async def market_pack(tn: TrueNorth) -> dict[str, Any]:
    """Independent market weather. Failure is recorded, never invented."""
    out: dict[str, Any] = {"status": "ok", "fear_greed": None, "mvrv_z": None, "notes": []}
    try:
        fg = await tn.call("fear_greed", {"limit": 8})
        latest = (fg.get("meta") or {}).get("latest") or (fg.get("items") or [None])[-1]
        if isinstance(latest, dict):
            out["fear_greed"] = latest.get("value")
            out["fear_greed_btc"] = latest.get("btcPrice")
            items = fg.get("items") or []
            if len(items) >= 2 and items[0].get("value") is not None and items[-1].get("value") is not None:
                out["fear_greed_delta"] = items[-1]["value"] - items[0]["value"]
    except Exception as exc:
        out["status"] = "partial"
        out["notes"].append(f"fear_greed unavailable: {exc}")
    try:
        mvrv = await tn.call("mvrv", {"limit": 5})
        latest = (mvrv.get("meta") or {}).get("latest") or (mvrv.get("items") or [None])[-1]
        if isinstance(latest, dict):
            out["mvrv_z"] = latest.get("zScore")
            out["mvrv_ratio"] = latest.get("mvrvRatio")
    except Exception as exc:
        out["status"] = "partial"
        out["notes"].append(f"mvrv unavailable: {exc}")
    if out["fear_greed"] is None and out["mvrv_z"] is None:
        out["status"] = "unavailable"
    return out
