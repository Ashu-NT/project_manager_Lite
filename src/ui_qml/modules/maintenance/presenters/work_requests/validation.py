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
