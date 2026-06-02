"""Recurring calendar event CRUD service."""

from __future__ import annotations

from datetime import date, time
from typing import Optional

from sqlalchemy.orm import Session

from src.core.platform.auth.authorization import require_permission
from src.core.platform.calendar.contracts import (
    CalendarRecurringEventRepository,
    PlatformCalendarRepository,
)
from src.core.platform.calendar.domain.enterprise_calendar import (
    CalendarRecurringEvent,
    ImpactType,
    RecurringEventType,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError


_VALID_EVENT_TYPES = {t.value for t in RecurringEventType}
_VALID_IMPACT_TYPES = {t.value for t in ImpactType}


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
        user_session=None,
    ) -> None:
        self._session = session
        self._calendar_repo = calendar_repo
        self._event_repo = event_repo
        self._user_session = user_session

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
        scope_type: Optional[str] = None,
        scope_id: Optional[str] = None,
        capacity_impact_percent: Optional[float] = None,
        effective_to: Optional[date] = None,
        priority: int = 0,
    ) -> CalendarRecurringEvent:
        require_permission(
            self._user_session, "task.manage", operation_label="add recurring event"
        )
        self._require_calendar(calendar_id)
        self._validate_event(event_type, impact_type, start_time, end_time, recurrence_rule)
        if effective_to is not None and effective_to < effective_from:
            raise ValidationError("effective_to must be after effective_from.")

        event = CalendarRecurringEvent.create(
            calendar_id=calendar_id,
            title=title.strip(),
            event_type=event_type,
            recurrence_rule=recurrence_rule.strip(),
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
        return event

    def update_recurring_event(
        self,
        event_id: str,
        *,
        title: Optional[str] = None,
        event_type: Optional[str] = None,
        recurrence_rule: Optional[str] = None,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        impact_type: Optional[str] = None,
        capacity_impact_percent: Optional[float] = None,
        effective_from: Optional[date] = None,
        effective_to: Optional[date] = None,
        is_active: Optional[bool] = None,
        priority: Optional[int] = None,
    ) -> CalendarRecurringEvent:
        require_permission(
            self._user_session, "task.manage", operation_label="update recurring event"
        )
        event = self._event_repo.get(event_id)
        if event is None:
            raise NotFoundError(f"Recurring event '{event_id}' not found.")

        if title is not None:
            event.title = title.strip()
        if event_type is not None:
            event.event_type = event_type
        if recurrence_rule is not None:
            _validate_rrule(recurrence_rule)
            event.recurrence_rule = recurrence_rule.strip()
        if start_time is not None:
            event.start_time = start_time
        if end_time is not None:
            event.end_time = end_time
        if impact_type is not None:
            event.impact_type = impact_type
        if capacity_impact_percent is not None:
            event.capacity_impact_percent = capacity_impact_percent
        if effective_from is not None:
            event.effective_from = effective_from
        if effective_to is not None:
            event.effective_to = effective_to
        if is_active is not None:
            event.is_active = is_active
        if priority is not None:
            event.priority = priority

        self._event_repo.update(event)
        self._session.commit()
        return event

    def delete_recurring_event(self, event_id: str) -> None:
        require_permission(
            self._user_session, "task.manage", operation_label="delete recurring event"
        )
        event = self._event_repo.get(event_id)
        if event is None:
            raise NotFoundError(f"Recurring event '{event_id}' not found.")
        self._event_repo.delete(event_id)
        self._session.commit()

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

    def _require_calendar(self, calendar_id: str) -> None:
        if self._calendar_repo.get(calendar_id) is None:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")

    def _validate_event(
        self,
        event_type: str,
        impact_type: str,
        start_time: time,
        end_time: time,
        recurrence_rule: str,
    ) -> None:
        if event_type not in _VALID_EVENT_TYPES:
            raise ValidationError(
                f"Invalid event_type '{event_type}'. Valid: {sorted(_VALID_EVENT_TYPES)}"
            )
        if impact_type not in _VALID_IMPACT_TYPES:
            raise ValidationError(
                f"Invalid impact_type '{impact_type}'. Valid: {sorted(_VALID_IMPACT_TYPES)}"
            )
        start_min = start_time.hour * 60 + start_time.minute
        end_min = end_time.hour * 60 + end_time.minute
        if end_min <= start_min:
            raise ValidationError("start_time must be before end_time.")
        _validate_rrule(recurrence_rule)


__all__ = ["RecurringEventService"]
