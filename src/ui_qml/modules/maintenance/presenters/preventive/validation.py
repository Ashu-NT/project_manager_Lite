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

def optional_bool(payload: dict[str, Any], key: str, default: bool) -> bool:
    value = payload.get(key, default)
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return default
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return bool(value)

def optional_optional_bool(payload: dict[str, Any], key: str) -> bool | None:
    if key not in payload or payload.get(key, None) is None:
        return None
    return optional_bool(payload, key, False)
