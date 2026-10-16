"""Transport-neutral normalization shared by resource command handlers."""

from __future__ import annotations

from datetime import date


def parse_certification_date(value: date | str | None) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except (ValueError, AttributeError):
        return None
