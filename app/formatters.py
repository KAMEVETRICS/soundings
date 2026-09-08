from __future__ import annotations

from typing import Any


def money(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "—"
    sign = "-" if number < 0 else ""
    number = abs(number)
    if number >= 1000:
        body = f"{number:,.2f}"
    elif number >= 1:
        body = f"{number:.4f}".rstrip("0").rstrip(".")
    elif number >= 0.01:
        body = f"{number:.6f}".rstrip("0").rstrip(".")
    else:
        body = f"{number:.8f}".rstrip("0").rstrip(".")
    return f"{sign}{body}"


def pct(value: Any, *, signed: bool = False) -> str:
    number = _num(value)
    if number is None:
        return "—"
    if signed:
        return f"{number:+.2f}%"
    return f"{number:.2f}%"


def usd_compact(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "—"
    sign = "-" if number < 0 else ""
    number = abs(number)
    if number >= 1_000_000_000_000:
        body = f"{number / 1_000_000_000_000:.2f}T"
    elif number >= 1_000_000_000:
        body = f"{number / 1_000_000_000:.2f}B"
    elif number >= 1_000_000:
        body = f"{number / 1_000_000:.2f}M"
    elif number >= 1_000:
        body = f"{number / 1_000:.2f}K"
    else:
        body = f"{number:.2f}"
    return f"{sign}${body}"


def compact(value: Any, digits: int = 2) -> str:
    number = _num(value)
    if number is None:
        return "—"
    return f"{number:.{digits}f}"


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        from jinja2.runtime import Undefined

        if isinstance(value, Undefined):
            return None
    except Exception:
        pass
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number
