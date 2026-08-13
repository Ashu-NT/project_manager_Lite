"""Recurring calendar event CRUD service."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, time
from typing import Any, Callable

from sqlalchemy.orm import Session

from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.contract.time_management.calendar.contracts import (
    CalendarRecurringEventRepository,
    PlatformCalendarRepository,
)
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    CalendarRecurringEvent,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError


def _validate_rrule(rule_str: str) -> None:
    try:
        from datetime import datetime
        from dateutil.rrule import rrulestr

        rrulestr(rule_str, dtstart=datetime(2024, 1, 1))
    except Exception as exc:
        raise ValidationError(f"Invalid recurrence_rule: {exc}") from exc


class RecurringEventService:
    def __init__(
        self,
        session: Session,
        calendar_repo: PlatformCalendarRepository,
        event_repo: CalendarRecurringEventRepository,
        user_session: Any = None,
        on_calendar_data_changed: Callable[[], None] | None = None,
    ) -> None:
        self._session = session
        self._calendar_repo = calendar_repo
        self._event_repo = event_repo
        self._user_session = user_session
        # Invalidates the (process-lifetime) EnterpriseCalendarResolver's
        # recurring-event cache — without this, a saved/deleted event stays
        # invisible to every resolver-backed read until the app restarts.
        self._on_calendar_data_changed = on_calendar_data_changed

    def list_recurring_events(
        self, calendar_id: str, *, active_only: bool = True
    ) -> list[CalendarRecurringEvent]:
        require_permission(
            self._user_session, "task.read", operation_label="list recurring events"
        )
        self._require_calendar(calendar_id)
        return self._event_repo.list_for_calendar(calendar_id, active_only=active_only)

    def add_recurring_event(
        self,
        calendar_id: str,
        *,
        title: str,
        event_type: str,
        recurrence_rule: str,
        start_time: time,
        end_time: time,
        impact_type: str,
        effective_from: date,
        scope_type: str | None = None,
        scope_id: str | None = None,
        capacity_impact_percent: float | None = None,
        effective_to: date | None = None,
        priority: int = 0,
    ) -> CalendarRecurringEvent:
        require_permission(
            self._user_session, "task.manage", operation_label="add recurring event"
        )
        self._require_calendar(calendar_id)
        _validate_rrule(recurrence_rule)

        event = CalendarRecurringEvent.create(
            calendar_id=calendar_id,
            title=title,
            event_type=event_type,
            recurrence_rule=recurrence_rule,
            start_time=start_time,
            end_time=end_time,
            impact_type=impact_type,
            effective_from=effective_from,
            scope_type=scope_type,
            scope_id=scope_id,
            capacity_impact_percent=capacity_impact_percent,
            effective_to=effective_to,
            priority=priority,
        )
        self._event_repo.add(event)
        self._session.commit()
        self._invalidate_resolver_cache()
        return event

    def update_recurring_event(
        self,
        event_id: str,
        *,
        title: str | None = None,
        event_type: str | None = None,
        recurrence_rule: str | None = None,
        start_time: time | None = None,
        end_time: time | None = None,
        impact_type: str | None = None,
        capacity_impact_percent: float | None = None,
        effective_from: date | None = None,
        effective_to: date | None = None,
        is_active: bool | None = None,
        priority: int | None = None,
    ) -> CalendarRecurringEvent:
        require_permission(
            self._user_session, "task.manage", operation_label="update recurring event"
        )
        event = self._event_repo.get(event_id)
        if event is None:
            raise NotFoundError(f"Recurring event '{event_id}' not found.")

        updated_rule = event.recurrence_rule if recurrence_rule is None else recurrence_rule
        _validate_rrule(updated_rule)
        updated = replace(
            event,
            title=event.title if title is None else title,
            event_type=event.event_type if event_type is None else event_type,
            recurrence_rule=updated_rule,
            start_time=event.start_time if start_time is None else start_time,
            end_time=event.end_time if end_time is None else end_time,
            impact_type=event.impact_type if impact_type is None else impact_type,
            capacity_impact_percent=(
                event.capacity_impact_percent
                if capacity_impact_percent is None
                else capacity_impact_percent
            ),
            effective_from=event.effective_from if effective_from is None else effective_from,
            effective_to=event.effective_to if effective_to is None else effective_to,
            is_active=event.is_active if is_active is None else is_active,
            priority=event.priority if priority is None else priority,
        )

        self._event_repo.update(updated)
        self._session.commit()
        self._invalidate_resolver_cache()
        return updated

    def delete_recurring_event(self, event_id: str) -> None:
        require_permission(
            self._user_session, "task.manage", operation_label="delete recurring event"
        )
        event = self._event_repo.get(event_id)
        if event is None:
            raise NotFoundError(f"Recurring event '{event_id}' not found.")
        self._event_repo.delete(event_id)
        self._session.commit()
        self._invalidate_resolver_cache()

    def expand_occurrences(
        self, event_id: str, start: date, end: date
    ) -> list[date]:
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
        except Exception:
            return []

    def _invalidate_resolver_cache(self) -> None:
        if self._on_calendar_data_changed is not None:
            self._on_calendar_data_changed()

    def _require_calendar(self, calendar_id: str) -> None:
        if self._calendar_repo.get(calendar_id) is None:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")


__all__ = ["RecurringEventService"]
