from __future__ import annotations


def normalize_filter(value: str, default: str = "all") -> str:
    return (value or "").strip() or default


def normalize_id(value: str) -> str:
    return (value or "").strip()
