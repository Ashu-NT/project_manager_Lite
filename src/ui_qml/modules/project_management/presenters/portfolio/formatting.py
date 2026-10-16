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


def format_percent(value: float | None, *, fallback: str = "0.0%") -> str:
    if value is None:
        return fallback
    return f"{float(value):.1f}%"


def format_signed_percent(value: float | None) -> str:
    if value is None:
        return "0.0%"
    return f"{float(value):+.1f}%"


def format_signed_int(value: int | None) -> str:
    return f"{int(value or 0):+d}"


__all__ = ["format_percent", "format_signed_int", "format_signed_percent"]
