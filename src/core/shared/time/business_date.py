"""Single place that converts a UTC instant into a business-local calendar
date. Every record in this codebase is stored in UTC; a "today" used to
decide which calendar/assignment is currently effective must be resolved in
the relevant timezone at the point of use, not the server's local time --
otherwise a server running in UTC can flip an assignment or working-day
boundary a day early/late for an organization configured in a different
timezone. Centralized here so no consumer reimplements this conversion
independently (see PlatformCalendarResolver.business_today for the
calendar-aware caller)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo


def business_today(timezone_name: str | None, *, now: datetime | None = None) -> date:
    """Today's date as observed in `timezone_name`. Falls back to UTC for a
    missing or unrecognized timezone identifier -- callers must still accept
    and display an unrecognized value elsewhere (see is_known_timezone);
    resolving "today" is never allowed to raise."""
    instant = now if now is not None else datetime.now(UTC)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    name = (timezone_name or "").strip() or "UTC"
    try:
        zone = ZoneInfo(name)
    except Exception:  # noqa: BLE001
        zone = ZoneInfo("UTC")
    return instant.astimezone(zone).date()


__all__ = ["business_today"]
