"""Shared, transport-neutral working-calendar results."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class WorkingCalendarHolidayDto:
    id: str
    date: date
    name: str


@dataclass(frozen=True, slots=True)
class WorkingDayCalculationDto:
    start_date: date
    working_days: int
    result_date: date
    skipped_non_working_days: int
