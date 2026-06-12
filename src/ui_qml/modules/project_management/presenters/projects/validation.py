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

def optional_float(payload: dict[str, Any], key: str) -> float | None:
    value = str(payload.get(key, "") or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError("Planned budget must be a valid number.") from exc

def optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value in (None, ""):
        return None
    return int(value)

def optional_date(payload: dict[str, Any], key: str) -> date | None:
    value = str(payload.get(key, "") or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"{key.replace('Date', ' date').replace('_', ' ').title()} must use YYYY-MM-DD."
        ) from exc
