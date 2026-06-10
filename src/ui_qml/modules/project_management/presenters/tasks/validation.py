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


def optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = str(payload.get(key, "") or "").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(
            f"{key.replace('_', ' ').replace('Days', ' days').title()} "
            "must be a whole number."
        ) from exc


def coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        result: list[str] = []
        for item in value:
            normalized = str(item or "").strip()
            if normalized:
                result.append(normalized)
        return result
    normalized = str(value or "").strip()
    return [normalized] if normalized else []


def optional_float(payload: dict[str, Any], key: str) -> float | None:
    value = str(payload.get(key, "") or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(
            f"{key.replace('Logged', ' logged').replace('_', ' ').title()} "
            "must be a valid number."
        ) from exc


def require_float(payload: dict[str, Any], key: str, message: str) -> float:
    value = optional_float(payload, key)
    if value is None:
        raise ValueError(message)
    return value


def optional_date(payload: dict[str, Any], key: str) -> date | None:
    value = str(payload.get(key, "") or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"{key.replace('Date', ' date').replace('_', ' ').title()} "
            "must use YYYY-MM-DD."
        ) from exc


def require_date(payload: dict[str, Any], key: str, message: str) -> date:
    value = optional_date(payload, key)
    if value is None:
        raise ValueError(message)
    return value


def optional_iso_date(value: str) -> date | None:
    normalized_value = str(value or "").strip()
    if not normalized_value:
        return None
    try:
        return date.fromisoformat(normalized_value)
    except ValueError as exc:
        raise ValueError("Dates must use YYYY-MM-DD.") from exc
