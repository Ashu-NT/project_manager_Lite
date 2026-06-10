from __future__ import annotations

from datetime import date
from typing import Any


def require_identifier(value: str, message: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError(message)
    return normalized


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
        raise ValueError(f"{key} must be a valid number.") from exc


def optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = str(payload.get(key, "") or "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{key} must be a valid integer.") from exc


def optional_date(payload: dict[str, Any], key: str) -> date | None:
    value = str(payload.get(key, "") or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{key} must use YYYY-MM-DD format.") from exc


def require_positive_float(payload: dict[str, Any], key: str, message: str) -> float:
    value = optional_float(payload, key)
    if value is None or value <= 0:
        raise ValueError(message)
    return value


def require_non_negative_float(payload: dict[str, Any], key: str, message: str) -> float:
    value = optional_float(payload, key)
    if value is None or value < 0:
        raise ValueError(message)
    return value
