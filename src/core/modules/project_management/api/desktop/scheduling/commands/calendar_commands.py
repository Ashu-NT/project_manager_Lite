from __future__ import annotations
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class SchedulingCalendarUpdateCommand:
    working_days: tuple[int, ...]
    hours_per_day: float


@dataclass(frozen=True)
class SchedulingHolidayCreateCommand:
    holiday_date: date
    name: str = ""


__all__ = ["SchedulingCalendarUpdateCommand", "SchedulingHolidayCreateCommand"]
