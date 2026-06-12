"""Date and datetime formatting helpers."""

from __future__ import annotations
from datetime import date, datetime, timezone


def fmt_date(value: date | None) -> str:
    if value is None:
        return "Not scheduled"
    return value.strftime("%Y-%m-%d")


def coerce_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def fmt_utc_datetime(value: datetime | None) -> str:
    resolved = coerce_utc_datetime(value)
    if resolved is None:
        return ""
    return resolved.strftime("%Y-%m-%d %H:%M")


__all__ = ["coerce_utc_datetime", "fmt_date", "fmt_utc_datetime"]
