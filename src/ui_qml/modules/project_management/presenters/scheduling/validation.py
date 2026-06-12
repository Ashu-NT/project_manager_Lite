from __future__ import annotations

from datetime import date
from typing import Any

def require_text(payload: dict[str, Any], key: str, message: str) -> str:
    value = str(payload.get(key, "") or "").strip()
    if not value:
        raise ValueError(message)
    return value

def optional_text(payload: dict[str, Any], key: str) -> str | None:
    value = str(payload.get(key, "") or "").strip()
    return value or None

def require_int(payload: dict[str, Any], key: str, message: str) -> int:
    value = str(payload.get(key, "") or "").strip()
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(message) from exc

def require_float(payload: dict[str, Any], key: str, message: str) -> float:
    value = str(payload.get(key, "") or "").strip()
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(message) from exc
    if parsed <= 0:
        raise ValueError(message)
    return parsed

def require_date(payload: dict[str, Any], key: str, message: str) -> date:
    value = str(payload.get(key, "") or "").strip()
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(message) from exc

__all__ = [
    "require_text",
    "optional_text",
    "require_int",
    "require_float",
    "require_date",
]
