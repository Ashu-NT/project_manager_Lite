from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from src.core.platform.contract.time_management.calendar.calendar_protocol import CalendarProtocol


@dataclass(frozen=True, slots=True)
class WorkingDaySnapshotCalendar:
    """In-memory calendar for a pre-resolved bounded scheduling horizon."""

    start: date
    end: date
    working_dates: frozenset[date]
    fallback: CalendarProtocol

    def is_working_day(self, target_date: date) -> bool:
        if self.start <= target_date <= self.end:
            return target_date in self.working_dates
        return self.fallback.is_working_day(target_date)

    def next_working_day(self, target_date: date, include_today: bool = True) -> date:
        current = target_date if include_today else target_date + timedelta(days=1)
        for _ in range(14_600):
            if self.is_working_day(current):
                return current
            current += timedelta(days=1)
        return current

    def add_working_days(self, start: date, working_days: int) -> date:
        if working_days == 0:
            return start
        if working_days > 0:
            current = self.next_working_day(start, include_today=True)
            remaining = working_days - 1
            while remaining > 0:
                current += timedelta(days=1)
                if self.is_working_day(current):
                    remaining -= 1
            return current
        current = start
        remaining = -working_days
        while remaining > 0:
            current -= timedelta(days=1)
            if self.is_working_day(current):
                remaining -= 1
        return current

    def working_days_between(self, start: date, end: date) -> int:
        if end < start:
            return 0
        if self.start <= start and end <= self.end:
            return sum(1 for day in self.working_dates if start <= day <= end)
        return self.fallback.working_days_between(start, end)


__all__ = ["WorkingDaySnapshotCalendar"]
