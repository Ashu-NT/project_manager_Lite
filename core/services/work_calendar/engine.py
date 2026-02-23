# core/services/work_calendar_engine.py
from datetime import date, timedelta
from typing import Set
from core.interfaces import WorkingCalendarRepository
from core.models import WorkingCalendar


class WorkCalendarEngine:
    def __init__(self, calendar_repo: WorkingCalendarRepository, calendar_id: str = "default"):
        self._repo: WorkingCalendarRepository = calendar_repo
        self._calendar_id: str = calendar_id

    def _get_calendar(self) -> WorkingCalendar:
        cal = self._repo.get(self._calendar_id)
        if cal is None:
            # ephemeral default, not persisted
            return WorkingCalendar.create_default()
        return cal
  
    def _get_working_days(self) -> Set[int]:
        return self._get_calendar().working_days

    def is_working_day(self, d: date) -> bool:
        cal = self._get_calendar()
        if d.weekday() not in cal.working_days:
            return False
        holidays = self._repo.list_holidays(cal.id) if cal.id else []
        return all(h.date != d for h in holidays)

    def next_working_day(self, d: date, include_today: bool = True) -> date:
        current = d
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

        # negative shift
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

