"""Date and datetime formatting helpers."""

from __future__ import annotations
from datetime import date, datetime


def format_date(value: date | None) -> str:
    if value is None:
        return "Not scheduled"
    return value.isoformat()


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M")


__all__ = ["format_date", "format_datetime"]
