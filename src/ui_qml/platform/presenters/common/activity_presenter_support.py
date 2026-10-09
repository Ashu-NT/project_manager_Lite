"""Shared helpers for entity-scoped Activity tab presenters (Organization,
Site, ...) built on the canonical ActivityItemViewModel/App.Widgets.
ActivityFeed architecture -- factored out here once a second entity-scoped
Activity presenter needed the exact same date-range filter and
human_message convention Organization Detail's Activity tab already used,
so neither presenter re-implements it."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

ACTIVITY_DATE_FILTER_OPTIONS: tuple[dict[str, str], ...] = (
    {"value": "", "label": "All time"},
    {"value": "today", "label": "Today"},
    {"value": "7d", "label": "Last 7 days"},
    {"value": "30d", "label": "Last 30 days"},
)


def since_for_date_range(date_range: str) -> datetime | None:
    now = datetime.now(timezone.utc)
    if date_range == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if date_range == "7d":
        return now - timedelta(days=7)
    if date_range == "30d":
        return now - timedelta(days=30)
    return None


def split_human_message(message: str) -> tuple[str, str]:
    """"Site created — Hamburg Office" -> ("Site created", "Hamburg Office").
    Every create/update/lifecycle human_message recorded for Organization/
    Site/Department/Employee/Document activity is written as "<verb
    phrase> — <subject>" (see site_commands.py/department_commands.py/
    employee_service.py/organization_service.py/document_commands.py).
    Falls back to the whole message as the title when the separator isn't
    present, rather than guessing at a split that isn't there."""
    if " — " in message:
        title, _, remainder = message.partition(" — ")
        return title.strip(), remainder.strip()
    return message.strip(), ""


__all__ = [
    "ACTIVITY_DATE_FILTER_OPTIONS",
    "since_for_date_range",
    "split_human_message",
]
