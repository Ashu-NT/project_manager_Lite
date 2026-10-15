"""Calendar working calendars inputs and results."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class WorkingCalendarUpdateCommand:
    working_days: tuple[int, ...]
    hours_per_day: float


@dataclass(frozen=True)
class WorkingCalendarHolidayCreateCommand:
    holiday_date: date
    name: str = ""
