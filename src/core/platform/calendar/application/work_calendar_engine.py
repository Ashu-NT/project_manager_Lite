from __future__ import annotations

from datetime import date, timedelta

from src.core.platform.calendar.contracts import WorkingCalendarRepository
from src.core.platform.calendar.domain import WorkingCalendar


class WorkCalendarEngine:
    def __init__(
        self,
        calendar_repo: WorkingCalendarRepository,
        calendar_id: str = "default",
    ) -> None:
        self._repo = calendar_repo
        self._calendar_id = calendar_id

    def _get_calendar(self) -> WorkingCalendar:
        calendar = self._repo.get(self._calendar_id)
        if calendar is None:
            return WorkingCalendar.create_default()
        return calendar

    def is_working_day(self, target_date: date) -> bool:
        calendar = self._get_calendar()
        if target_date.weekday() not in calendar.working_days:
            return False
        holidays = self._repo.list_holidays(calendar.id) if calendar.id else []
        return all(holiday.date != target_date for holiday in holidays)

    def next_working_day(self, target_date: date, include_today: bool = True) -> date:
        current = target_date
        if not include_today:
            current += timedelta(days=1)
        while not self.is_working_day(current):
            current += timedelta(days=1)
        return current

    def add_working_days(self, start: date, working_days: int) -> date:
        if working_days == 0:
            return start

        if working_days > 0:
            current = self.next_working_day(start, include_today=True)
            days_remaining = working_days - 1
            while days_remaining > 0:
                current += timedelta(days=1)
                if self.is_working_day(current):
                    days_remaining -= 1
            return current

        days_remaining = -working_days
        current = self.next_working_day(start, include_today=True)
        while days_remaining > 0:
            current -= timedelta(days=1)
            if self.is_working_day(current):
                days_remaining -= 1
        return current

    def working_days_between(self, start: date, end: date) -> int:
        if end < start:
            return 0
        current = start
        count = 0
        while current <= end:
            if self.is_working_day(current):
                count += 1
            current += timedelta(days=1)
        return count


__all__ = ["WorkCalendarEngine"]
