from __future__ import annotations


def normalized_filter(value: str) -> str:
    normalized = str(value or "").strip()
    return "" if normalized in {"", "all"} else normalized
