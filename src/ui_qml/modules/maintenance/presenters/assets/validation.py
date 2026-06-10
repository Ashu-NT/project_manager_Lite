from __future__ import annotations

from typing import Any


def require_text(payload: dict[str, Any], key: str, message: str) -> str:
    value = str(payload.get(key, "") or "").strip()
    if not value:
        raise ValueError(message)
    return value


def require_identifier(value: str, message: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError(message)
    return normalized


def optional_text(payload: dict[str, Any], key: str) -> str | None:
    value = str(payload.get(key, "") or "").strip()
    return value or None


def require_int(payload: dict[str, Any], key: str, message: str) -> int:
    value = payload.get(key, None)
    if value in (None, ""):
        raise ValueError(message)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(message) from exc


def optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key, None)
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be a whole number.") from exc


def optional_float(payload: dict[str, Any], key: str) -> float | None:
    value = payload.get(key, None)
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be a number.") from exc


def bool_value(payload: dict[str, Any], key: str, default: bool) -> bool:
    return bool(payload.get(key, default))
