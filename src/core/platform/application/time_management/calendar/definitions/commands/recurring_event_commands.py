"""Calendar recurring event operations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import time
from typing import Any, cast

from sqlalchemy.orm import Session

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.time_management.calendar._input import (
    parse_date as _parse_date,
)
from src.core.platform.application.time_management.calendar._input import (
    parse_time as _parse_time,
)
from src.core.platform.application.time_management.calendar._input import required_date
from src.core.platform.application.time_management.calendar.definitions.dto.commands.recurring_events import (
    RecurringEventCreateCommand,
    RecurringEventUpdateCommand,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.contract.repositories.time_management.calendar.contracts import (
    CalendarRecurringEventRepository,
    PlatformCalendarRepository,
)
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    CalendarRecurringEvent,
)


def _validate_rrule(rule_str: str) -> None:
    try:
        from datetime import datetime

        from dateutil.rrule import rrulestr

        # Fixed naive probe date: only checks that the rule parses.
        rrulestr(rule_str, dtstart=datetime(2024, 1, 1))  # noqa: DTZ001
    except Exception as exc:
        raise ValidationError(f"Invalid recurrence_rule: {exc}") from exc


class RecurringEventCommandHandler:
    """Transactional writes for recurring event."""

    def __init__(
        self,
        *,
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
        self._on_calendar_data_changed = on_calendar_data_changed

    def add_recurring_event(
        self, command: RecurringEventCreateCommand
    ) -> CalendarRecurringEvent:
        calendar_id = command.calendar_id
        title = command.title
        event_type = command.event_type
        recurrence_rule = command.recurrence_rule
        start_time = cast(time, _parse_time(command.start_time))
        end_time = cast(time, _parse_time(command.end_time))
        impact_type = command.impact_type
        effective_from = required_date(command.effective_from)
        scope_type = command.scope_type or None
        scope_id = command.scope_id or None
        capacity_impact_percent = command.capacity_impact_percent
        effective_to = _parse_date(command.effective_to)
        priority = command.priority

        require_permission(
            self._user_session, "calendar.manage", operation_label="add recurring event"
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
        self, command: RecurringEventUpdateCommand
    ) -> CalendarRecurringEvent:
        event_id = command.event_id
        title = command.title or None
        event_type = command.event_type or None
        recurrence_rule = command.recurrence_rule or None
        start_time = _parse_time(command.start_time)
        end_time = _parse_time(command.end_time)
        impact_type = command.impact_type or None
        capacity_impact_percent = command.capacity_impact_percent
        effective_from = _parse_date(command.effective_from)
        effective_to = _parse_date(command.effective_to)
        is_active = command.is_active
        priority = command.priority

        require_permission(
            self._user_session,
            "calendar.manage",
            operation_label="update recurring event",
        )
        event = self._event_repo.get(event_id)
        if event is None:
            raise NotFoundError(f"Recurring event '{event_id}' not found.")

        updated_rule = (
            event.recurrence_rule if recurrence_rule is None else recurrence_rule
        )
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
            effective_from=event.effective_from
            if effective_from is None
            else effective_from,
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
            self._user_session,
            "calendar.manage",
            operation_label="delete recurring event",
        )
        event = self._event_repo.get(event_id)
        if event is None:
            raise NotFoundError(f"Recurring event '{event_id}' not found.")
        self._event_repo.delete(event_id)
        self._session.commit()
        self._invalidate_resolver_cache()

    def _invalidate_resolver_cache(self) -> None:
        if self._on_calendar_data_changed is not None:
            self._on_calendar_data_changed()

    def _require_calendar(self, calendar_id: str) -> None:
        if self._calendar_repo.get(calendar_id) is None:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")


__all__ = ["RecurringEventCommandHandler"]
