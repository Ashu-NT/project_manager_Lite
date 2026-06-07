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

import logging
from datetime import date, timedelta

from src.core.platform.calendar.application.enterprise_calendar_resolver import (
    EnterpriseCalendarResolver,
)


logger = logging.getLogger(__name__)


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
        # Small moves should fail fast if the calendar is misconfigured. Large
        # moves are still capped so bad data cannot scan decades indefinitely.
        max_iter = min(max(abs(working_days) * 7, 730), 365 * 40)
        if working_days > 0:
            current = self.next_working_day(start, include_today=True)
            remaining = working_days - 1
            iterations = 0
            while remaining > 0 and iterations < max_iter:
                current += timedelta(days=1)
                if self.is_working_day(current):
                    remaining -= 1
                iterations += 1
            if remaining > 0:
                logger.warning(
                    "Global calendar add_working_days exhausted search start=%s working_days=%s remaining=%s iterations=%s",
                    start,
                    working_days,
                    remaining,
                    iterations,
                )
            return current

        remaining = -working_days
        current = start
        iterations = 0
        while remaining > 0 and iterations < max_iter:
            current -= timedelta(days=1)
            if self.is_working_day(current):
                remaining -= 1
            iterations += 1
        if remaining > 0:
            logger.warning(
                "Global calendar add_working_days exhausted reverse search start=%s working_days=%s remaining=%s iterations=%s",
                start,
                working_days,
                remaining,
                iterations,
            )
        return current

    def working_days_between(self, start: date, end: date) -> int:
        if end < start:
            return 0
        # Use resolve_range for bulk efficiency — single set of DB queries for entire range
        try:
            days = self._resolver.resolve_range(start=start, end=end)
            return sum(1 for d in days if d.available_hours > 0)
        except Exception:
            # Fallback: day-by-day (safe but slower)
            count = 0
            current = start
            while current <= end:
                if self.is_working_day(current):
                    count += 1
                current += timedelta(days=1)
            return count


__all__ = ["GlobalCalendarShim"]
