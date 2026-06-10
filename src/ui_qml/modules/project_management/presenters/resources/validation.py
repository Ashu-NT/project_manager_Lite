from __future__ import annotations

from typing import Any


def require_text(payload: dict[str, Any], key: str, message: str) -> str:
    value = str(payload.get(key, "") or "").strip()
    if not value:
        raise ValueError(message)
    return value


def optional_text(payload: dict[str, Any], key: str) -> str | None:
    value = str(payload.get(key, "") or "").strip()
    return value or None


def optional_float(
    payload: dict[str, Any],
    key: str,
    message: str,
    *,
    default: float,
) -> float:
    value = str(payload.get(key, "") or "").strip()
    if not value:
        return float(default)
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(message) from exc


def optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value in (None, ""):
        return None
    return int(value)


def optional_bool(payload: dict[str, Any], key: str, *, default: bool) -> bool:
    value = payload.get(key)
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
