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


def build_actor_lookup(user_api) -> dict[str, str]:
    """actor_id (a User id) -> human-readable name, preferring User.
    display_name, then username, then email -- never a raw user id. A
    caller with its own richer resolution (e.g. linking through Employee.
    full_name) should call this first and .update() its own entries on
    top, so its higher-priority source wins only where it actually has a
    value. A user not present here resolves to "" and the caller decides
    the final "Deleted user"/"System" fallback."""
    if user_api is None:
        return {}
    result = user_api.list_users()
    if not result.ok or result.data is None:
        return {}
    fallback: dict[str, str] = {}
    display_name: dict[str, str] = {}
    for user in result.data:
        name = str(user.username or "").strip() or str(user.email or "").strip()
        if name:
            fallback[user.id] = name
        explicit = str(user.display_name or "").strip()
        if explicit:
            display_name[user.id] = explicit
    lookup: dict[str, str] = {}
    lookup.update(fallback)
    lookup.update(display_name)
    return lookup


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
    "build_actor_lookup",
    "since_for_date_range",
    "split_human_message",
]
