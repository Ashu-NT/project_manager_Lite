"""Normalize calendar inputs independently of Desktop transport code."""

from datetime import date, time


def parse_date(value: date | str | None) -> date | None:
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def required_date(value: date | str) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


def parse_time(value: time | str | None) -> time | None:
    if isinstance(value, time):
        return value
    if not value:
        return None
    try:
        parts = value.split(":")
        return time(int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
    except (ValueError, IndexError):
        return None
