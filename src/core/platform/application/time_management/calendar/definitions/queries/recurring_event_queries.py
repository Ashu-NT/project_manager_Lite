"""Calendar recurring event operations."""

from __future__ import annotations

from datetime import date, time
from typing import Any


from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.contract.repositories.time_management.calendar.contracts import (
    CalendarRecurringEventRepository,
    PlatformCalendarRepository,
)
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    CalendarRecurringEvent,
)


class RecurringEventQueryHandler:
    """Read-only lookups for recurring event."""

    def __init__(
        self,
        *,
        calendar_repo: PlatformCalendarRepository,
        event_repo: CalendarRecurringEventRepository,
        user_session: Any = None,
    ) -> None:
        self._calendar_repo = calendar_repo
        self._event_repo = event_repo
        self._user_session = user_session

    def list_recurring_events(
        self, calendar_id: str, *, active_only: bool = True
    ) -> list[CalendarRecurringEvent]:
        require_permission(
            self._user_session, "calendar.read", operation_label="list recurring events"
        )
        self._require_calendar(calendar_id)
        return self._event_repo.list_for_calendar(calendar_id, active_only=active_only)

    def expand_occurrences(self, event_id: str, start: date, end: date) -> list[date]:
        """Return all dates in [start, end] where this event fires."""
        event = self._event_repo.get(event_id)
        if event is None:
            raise NotFoundError(f"Recurring event '{event_id}' not found.")
        try:
            from datetime import datetime

            from dateutil.rrule import rrulestr

            dtstart = datetime.combine(event.effective_from, event.start_time)
            rule = rrulestr(event.recurrence_rule, dtstart=dtstart, ignoretz=True)
            range_start = datetime.combine(start, time(0, 0))
            range_end = datetime.combine(end, time(23, 59, 59))
            return [dt.date() for dt in rule.between(range_start, range_end, inc=True)]
        except Exception:  # noqa: BLE001
            return []

    def _require_calendar(self, calendar_id: str) -> None:
        if self._calendar_repo.get(calendar_id) is None:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")


__all__ = ["RecurringEventQueryHandler"]
