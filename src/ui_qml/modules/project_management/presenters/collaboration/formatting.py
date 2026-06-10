from __future__ import annotations

from datetime import UTC, datetime


def iso_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "Timestamp unavailable"
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M")
