"""Date formatting helpers."""

from __future__ import annotations
from datetime import date


def format_date(value: date | None) -> str:
    if value is None:
        return "Not set"
    return value.isoformat()


__all__ = ["format_date"]
