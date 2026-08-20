"""R4.4W.1 -- a caching CalendarProtocol wrapper scoped to ONE
``ResourceLevelingPlanner.build_proposal`` call.

Profiling found the leveling Preview's real cost is neither the
planner's own orchestration (only ~7 run_cpm calls happen even at
5000 tasks) nor a resource-capacity rescan -- it is ``run_cpm``'s
canonical ``build_schedule_result`` calling ``calendar.
working_days_between`` once per task to compute float, plus
``add_working_days``/``is_working_day`` inside the forward/backward
passes, with NONE of it cached: at n=1000 real DB-backed tasks,
``working_days_between`` alone cost 5.05s across 1000 calls (mean
5ms/call), because every call re-resolves calendar facts through the
enterprise resolver (a DB round trip) from scratch.

This wrapper bulk-resolves the SAME authoritative working-day facts
ONCE per Preview via ``working_day_dates_between`` (a single query the
calendar already exposes), then answers ``is_working_day`` from an
in-memory set and ``working_days_between`` via a sorted-list count --
mathematically identical to summing the same set day by day, so there
is no semantic drift. ``add_working_days``/``next_working_day`` keep
the EXACT day-by-day loop structure the real calendar classes already
use (GlobalCalendarShim/ProjectCalendarAdapter/WorkingDaySnapshotCalendar),
just calling the fast cached ``is_working_day`` instead of re-querying.

Any date outside the precomputed window transparently falls back to
the real calendar -- correctness never depends on the window bound
being exactly right, only the amount of speedup does. This is an
index/cache over the SAME authoritative source, not a second
calendar engine and not a change to CPM math or scheduling semantics.
"""
from __future__ import annotations
import logging

import bisect
from datetime import date, timedelta

from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)

logger = logging.getLogger(__name__)

class MemoizingCalendarWindow:
    """Wraps ``real_calendar`` for one call scope. Construct once per
    ``build_proposal`` invocation with a generously bounded
    [window_start, window_end]; discard afterward."""

    def __init__(self, real_calendar: CalendarProtocol, window_start: date, window_end: date) -> None:
        self._real = real_calendar
        self._window_start = window_start
        self._window_end = window_end
        self._cache_ok = False
        self._working_dates: frozenset[date] = frozenset()
        self._sorted_dates: list[date] = []
        if window_start <= window_end:
            try:
                self._working_dates = real_calendar.working_day_dates_between(window_start, window_end)
                self._sorted_dates = sorted(self._working_dates)
                self._cache_ok = True
            except Exception:
                logger.debug(
                    "Unable to build preview-scoped calendar cache; "
                    "falling back to authoritative calendar.",
                    exc_info=True,
                )

    def _in_window(self, d: date) -> bool:
        return self._cache_ok and self._window_start <= d <= self._window_end

    def is_working_day(self, target_date: date) -> bool:
        if self._in_window(target_date):
            return target_date in self._working_dates
        return self._real.is_working_day(target_date)

    def next_working_day(self, target_date: date, include_today: bool = True) -> date:
        current = target_date if include_today else target_date + timedelta(days=1)
        if not self._in_window(current):
            return self._real.next_working_day(target_date, include_today=include_today)
        for _ in range(14_600):
            if current > self._window_end:
                return self._real.next_working_day(current, include_today=True)
            if self.is_working_day(current):
                return current
            current += timedelta(days=1)
        return self._real.next_working_day(current, include_today=True)

    def add_working_days(self, start: date, working_days: int) -> date:
        # Preserve the real calendar's exact semantics for zero-day movement
        # and for starts outside the cached window.
        if working_days == 0 or not self._in_window(start):
            return self._real.add_working_days(start, working_days)

        max_iter = min(max(abs(working_days) * 7, 730), 365 * 40)

        if working_days > 0:
            current = self.next_working_day(start, include_today=True)

            # next_working_day may legitimately leave the cached window.
            # In that case, re-run the ORIGINAL operation against the real
            # calendar rather than trying to continue from the cache boundary.
            if not self._in_window(current):
                return self._real.add_working_days(start, working_days)

            remaining = working_days - 1
            iterations = 0

            while remaining > 0 and iterations < max_iter:
                current += timedelta(days=1)

                # Cache window was not large enough. Correctness must not
                # depend on our window-size estimate.
                if current > self._window_end:
                    return self._real.add_working_days(start, working_days)

                if self.is_working_day(current):
                    remaining -= 1

                iterations += 1

            # Defensive guard for pathological calendars / long shutdowns.
            # Never return a partially advanced date.
            if remaining > 0:
                return self._real.add_working_days(start, working_days)

            return current

        # Negative movement.
        remaining = -working_days
        current = start
        iterations = 0

        while remaining > 0 and iterations < max_iter:
            current -= timedelta(days=1)

            # Same rule in the backward direction:
            # fall back using the ORIGINAL operation.
            if current < self._window_start:
                return self._real.add_working_days(start, working_days)

            if self.is_working_day(current):
                remaining -= 1

            iterations += 1

        # Never return a partially calculated result.
        if remaining > 0:
            return self._real.add_working_days(start, working_days)

        return current

    def working_days_between(self, start: date, end: date) -> int:
        if end < start:
            return 0
        if self._in_window(start) and self._in_window(end):
            lo = bisect.bisect_left(self._sorted_dates, start)
            hi = bisect.bisect_right(self._sorted_dates, end)
            return hi - lo
        return self._real.working_days_between(start, end)

    def working_day_dates_between(self, start: date, end: date) -> frozenset[date]:
        if self._in_window(start) and self._in_window(end):
            lo = bisect.bisect_left(self._sorted_dates, start)
            hi = bisect.bisect_right(self._sorted_dates, end)
            return frozenset(self._sorted_dates[lo:hi])
        return self._real.working_day_dates_between(start, end)


def build_memoizing_window_for_tasks(
    real_calendar: CalendarProtocol,
    tasks_by_id: dict,
    *,
    search_horizon_working_days: int,
) -> MemoizingCalendarWindow:
    """Computes a generous [window_start, window_end] covering every
    date fact any of ``tasks_by_id`` could plausibly need during CPM
    and leveling-candidate search, then builds the cache. Generous
    padding is safe -- an over-wide window costs one extra bulk query,
    never an incorrect answer; an under-wide one just falls back to
    the real calendar for the overflow, never wrong either."""
    known_dates: list[date] = []
    for task in tasks_by_id.values():
        for attr in ("start_date", "end_date", "constraint_date", "actual_start", "actual_end", "deadline",
                     "resource_leveling_not_before"):
            value = getattr(task, attr, None)
            if isinstance(value, date):
                known_dates.append(value)

    today = date.today()
    if not known_dates:
        known_dates = [today]

    # Generous calendar-day padding: search horizon (working days) can
    # roughly double in calendar days across weekends/holidays, plus a
    # flat safety margin for backward-pass/constraint edge cases.
    horizon_padding = timedelta(days=search_horizon_working_days * 2 + 60)
    window_start = min(known_dates) - timedelta(days=60)
    window_end = max(known_dates) + horizon_padding
    return MemoizingCalendarWindow(real_calendar, window_start, window_end)


__all__ = ["MemoizingCalendarWindow", "build_memoizing_window_for_tasks"]
