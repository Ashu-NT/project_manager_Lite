from __future__ import annotations

from datetime import date


def format_date(value: date | None) -> str:
    if value is None:
        return ""
    return value.isoformat()


def format_date_label(value: date | None) -> str:
    if value is None:
        return "Not set"
    # Matches the human-readable format already used elsewhere in PM
    # (e.g. Projects' format_date_label) rather than a raw ISO string.
    return value.strftime("%d %b %Y")


def shift_days_label(days: int) -> str:
    if days == 0:
        return "No change"
    if days > 0:
        return f"+{days}d"
    return f"{days}d"
