from __future__ import annotations

from dataclasses import dataclass

from src.core.platform.application.time_management.calendar.dto.responses.working_calendar import (
    WorkingCalendarHolidayDto,
)


@dataclass(frozen=True)
class WorkingCalendarOptionDto:
    value: str
    label: str
    summary_label: str


@dataclass(frozen=True)
class WorkingCalendarDayDto:
    index: int
    label: str
    checked: bool




@dataclass(frozen=True)
class WorkingCalendarSnapshotDto:
    id: str
    name: str
    working_days: tuple[WorkingCalendarDayDto, ...]
    hours_per_day: float
    holidays: tuple[WorkingCalendarHolidayDto, ...]
