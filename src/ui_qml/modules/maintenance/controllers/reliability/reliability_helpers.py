from __future__ import annotations


def normalized_filter(value: str) -> str:
    normalized = str(value or "").strip()
    return "" if normalized in {"", "all"} else normalized


def int_filter(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
