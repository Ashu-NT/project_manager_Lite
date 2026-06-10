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


def require_float(payload: dict[str, Any], key: str, message: str) -> float:
    value = payload.get(key)
    if value in (None, ""):
        raise ValueError(message)
    return float(value)


def require_date(payload: dict[str, Any], key: str, message: str) -> date:
    value = str(payload.get(key, "") or "").strip()
    if not value:
        raise ValueError(message)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Dates must use YYYY-MM-DD.") from exc


def optional_date(value: str) -> date | None:
    normalized_value = str(value or "").strip()
    if not normalized_value:
        return None
    try:
        return date.fromisoformat(normalized_value)
    except ValueError as exc:
        raise ValueError("Dates must use YYYY-MM-DD.") from exc
