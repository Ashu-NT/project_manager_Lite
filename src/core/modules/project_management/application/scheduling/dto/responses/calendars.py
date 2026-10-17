"""Immutable scheduling calendar facts, independent of display labels."""

from dataclasses import dataclass

from src.core.platform.application.time_management.calendar.dto.responses.working_calendar import (
    WorkingCalendarHolidayDto,
)


@dataclass(frozen=True, slots=True)
class SchedulingCalendarResponse:
    id: str
    name: str
    working_days: tuple[int, ...]
    hours_per_day: float


@dataclass(frozen=True, slots=True)
class SchedulingCalendarSnapshot:
    working_days: tuple[int, ...]
    hours_per_day: float
    holidays: tuple[WorkingCalendarHolidayDto, ...]
    calendar_id: str = ""
    calendar_name: str = ""
