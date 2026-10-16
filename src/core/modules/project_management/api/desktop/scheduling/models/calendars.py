from __future__ import annotations

from dataclasses import dataclass

_DAY_LABELS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


from src.core.platform.application.time_management.calendar.dto.responses.working_calendar import (
    WorkingCalendarHolidayDto,
)


@dataclass(frozen=True)
class SchedulingCalendarOptionDescriptor:
    value: str
    label: str
    summary_label: str


@dataclass(frozen=True)
class SchedulingDayDescriptor:
    index: int
    label: str
    checked: bool




@dataclass(frozen=True)
class SchedulingCalendarSnapshotDto:
    working_days: tuple[SchedulingDayDescriptor, ...]
    hours_per_day: float
    holidays: tuple[WorkingCalendarHolidayDto, ...]
    calendar_id: str = ""
    calendar_name: str = ""




__all__ = ['_DAY_LABELS', 'SchedulingCalendarOptionDescriptor', 'SchedulingCalendarSnapshotDto', 'SchedulingDayDescriptor']
