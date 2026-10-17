"""Snapshot mutable legacy calendars and aggregate platform calendar facts."""

from datetime import date
from typing import Any

from src.core.modules.project_management.application.scheduling.dto.responses.calendars import (
    SchedulingCalendarResponse,
    SchedulingCalendarSnapshot,
)
from src.core.platform.application.time_management.calendar.dto.responses.working_calendar import (
    WorkingCalendarHolidayDto,
)


def map_legacy_calendar(calendar: Any) -> SchedulingCalendarResponse:
    return SchedulingCalendarResponse(
        id=str(getattr(calendar, "id", "") or "default"),
        name=str(getattr(calendar, "name", "") or "Default Calendar").strip(),
        working_days=tuple(sorted(calendar.working_days or {0, 1, 2, 3, 4})),
        hours_per_day=float(calendar.hours_per_day or 8.0),
    )


def map_legacy_calendar_snapshot(
    calendar: Any, holidays: Any
) -> SchedulingCalendarSnapshot:
    facts = map_legacy_calendar(calendar)
    return SchedulingCalendarSnapshot(
        calendar_id=facts.id,
        calendar_name=facts.name,
        working_days=facts.working_days,
        hours_per_day=facts.hours_per_day,
        holidays=tuple(
            holiday
            if isinstance(holiday, WorkingCalendarHolidayDto)
            else WorkingCalendarHolidayDto(
                id=holiday.id,
                date=holiday.date,
                name=holiday.name or "",
            )
            for holiday in sorted(holidays, key=lambda item: item.date)
        ),
    )


def map_platform_calendar_snapshot(
    calendar: Any, rules: Any, exceptions: Any
) -> SchedulingCalendarSnapshot:
    rules_by_weekday = {rule.weekday: rule for rule in rules}
    working_hours = [
        rule.computed_hours
        for rule in rules
        if rule.is_working_day and rule.computed_hours
    ]
    return SchedulingCalendarSnapshot(
        calendar_id=calendar.id,
        calendar_name=calendar.name,
        working_days=tuple(
            i
            for i in range(7)
            if i in rules_by_weekday and rules_by_weekday[i].is_working_day
        ),
        hours_per_day=float(working_hours[0] if working_hours else 8.0),
        holidays=tuple(
            sorted(
                (
                    WorkingCalendarHolidayDto(
                        id=exc.id,
                        date=date.fromisoformat(exc.exception_date),
                        name=exc.name or "",
                    )
                    for exc in exceptions
                    if str(exc.exception_type or "").upper() == "HOLIDAY"
                    and exc.exception_date
                ),
                key=lambda item: item.date,
            )
        ),
    )
