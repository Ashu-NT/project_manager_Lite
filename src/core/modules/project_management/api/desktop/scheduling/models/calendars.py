from __future__ import annotations
from dataclasses import dataclass
from datetime import date

_DAY_LABELS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


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
class SchedulingHolidayDto:
    id: str
    date: date
    name: str


@dataclass(frozen=True)
class SchedulingCalendarSnapshotDto:
    working_days: tuple[SchedulingDayDescriptor, ...]
    hours_per_day: float
    holidays: tuple[SchedulingHolidayDto, ...]


@dataclass(frozen=True)
class SchedulingWorkingDayCalculationDto:
    start_date: date
    working_days: int
    result_date: date
    skipped_non_working_days: int


__all__ = [
    "_DAY_LABELS",
    "SchedulingCalendarOptionDescriptor",
    "SchedulingCalendarSnapshotDto",
    "SchedulingDayDescriptor",
    "SchedulingHolidayDto",
    "SchedulingWorkingDayCalculationDto",
]
