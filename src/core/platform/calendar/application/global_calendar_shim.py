"""
GlobalCalendarShim — drop-in replacement for WorkCalendarEngine backed by the enterprise resolver.

Provides the same interface (is_working_day, add_working_days, working_days_between,
next_working_day) but resolves working days from the enterprise GLOBAL calendar hierarchy
instead of the legacy working_calendars table.

Used for:
  - Services that need a calendar without knowing the specific project/resource context
    (DashboardService, BaselineService, PortfolioResourcePoolService, ReportingService)
  - The scheduling engine's _base_calendar (falls back here when no enterprise calendar
    bootstrapped and BoundProjectCalendar returns None)

For project-specific calculations use BoundProjectCalendar instead, which resolves
the full hierarchy: Global → Site → Department → Employee → Project → Resource.
"""

from __future__ import annotations

from datetime import date, timedelta

from src.core.platform.calendar.application.enterprise_calendar_resolver import (
    EnterpriseCalendarResolver,
)


class GlobalCalendarShim:
    """Enterprise-backed drop-in for WorkCalendarEngine using the GLOBAL calendar."""

    def __init__(self, resolver: EnterpriseCalendarResolver) -> None:
        self._resolver = resolver

    def is_working_day(self, target_date: date) -> bool:
        try:
            ctx = self._resolver.resolve_calendar_context(target_date=target_date)
            return ctx.available_hours > 0
        except Exception:
            return target_date.weekday() < 5

    def next_working_day(self, target_date: date, include_today: bool = True) -> date:
        current = target_date
        if not include_today:
            current += timedelta(days=1)
        for _ in range(730):
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

        remaining = -working_days
        current = start
        while remaining > 0:
            current -= timedelta(days=1)
            if self.is_working_day(current):
                remaining -= 1
        return current

    def working_days_between(self, start: date, end: date) -> int:
        if end < start:
            return 0
        count = 0
        current = start
        while current <= end:
            if self.is_working_day(current):
                count += 1
            current += timedelta(days=1)
        return count


__all__ = ["GlobalCalendarShim"]
