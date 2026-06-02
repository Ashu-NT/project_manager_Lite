from __future__ import annotations

from dataclasses import dataclass
from datetime import date


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
class WorkingCalendarHolidayDto:
    id: str
    date: date
    name: str


@dataclass(frozen=True)
class WorkingCalendarSnapshotDto:
    id: str
    name: str
    working_days: tuple[WorkingCalendarDayDto, ...]
    hours_per_day: float
    holidays: tuple[WorkingCalendarHolidayDto, ...]


@dataclass(frozen=True)
class WorkingCalendarUpdateCommand:
    working_days: tuple[int, ...]
    hours_per_day: float


@dataclass(frozen=True)
class WorkingCalendarHolidayCreateCommand:
    holiday_date: date
    name: str = ""


@dataclass(frozen=True)
class WorkingDayCalculationCommand:
    start_date: date
    working_days: int


@dataclass(frozen=True)
class WorkingDayCalculationDto:
    start_date: date
    working_days: int
    result_date: date
    skipped_non_working_days: int

