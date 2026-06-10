from __future__ import annotations

from datetime import date


def format_date(value: date | None) -> str:
    if value is None:
        return ""
    return value.isoformat()


def format_date_label(value: date | None) -> str:
    if value is None:
        return "Not scheduled"
    return value.isoformat()
