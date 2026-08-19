"""R4.4W.1 -- MemoizingCalendarWindow must be a pure performance cache:
every answer must exactly match the real, uncached calendar it wraps,
both inside and outside the precomputed window. Uses the REAL
services["work_calendar_engine"] (GlobalCalendarShim), not a synthetic
fake, since that's the calendar the leveling planner actually runs
against in production.
"""
from __future__ import annotations

from datetime import date, timedelta

from src.core.modules.project_management.application.scheduling.leveling.calendar_cache import (
    MemoizingCalendarWindow,
    build_memoizing_window_for_tasks,
)
from src.core.modules.project_management.domain.tasks.task import Task


class TestMemoizingCalendarWindowMatchesRealCalendar:
    def test_is_working_day_matches_inside_and_outside_window(self, services):
        real = services["work_calendar_engine"]
        window_start = date(2026, 1, 1)
        window_end = date(2026, 3, 31)
        cached = MemoizingCalendarWindow(real, window_start, window_end)

        probe_dates = [
            date(2026, 1, 5),  # inside window
            date(2026, 2, 14),  # inside window
            date(2026, 6, 1),  # outside window -- must defer to real
        ]
        for d in probe_dates:
            assert cached.is_working_day(d) == real.is_working_day(d), f"mismatch at {d}"

    def test_working_days_between_matches_inside_window(self, services):
        real = services["work_calendar_engine"]
        window_start = date(2026, 1, 1)
        window_end = date(2026, 3, 31)
        cached = MemoizingCalendarWindow(real, window_start, window_end)

        start, end = date(2026, 1, 5), date(2026, 2, 20)
        assert cached.working_days_between(start, end) == real.working_days_between(start, end)

    def test_working_days_between_matches_outside_window(self, services):
        real = services["work_calendar_engine"]
        cached = MemoizingCalendarWindow(real, date(2026, 1, 1), date(2026, 1, 31))

        start, end = date(2026, 6, 1), date(2026, 6, 30)
        assert cached.working_days_between(start, end) == real.working_days_between(start, end)

    def test_add_working_days_matches_inside_window(self, services):
        real = services["work_calendar_engine"]
        window_start = date(2026, 1, 1)
        window_end = date(2026, 3, 31)
        cached = MemoizingCalendarWindow(real, window_start, window_end)

        for start, n in [(date(2026, 1, 5), 5), (date(2026, 2, 1), 10), (date(2026, 1, 10), -3)]:
            assert cached.add_working_days(start, n) == real.add_working_days(start, n), (start, n)

    def test_add_working_days_falls_back_correctly_near_window_edge(self, services):
        """A walk that starts inside the window but needs more days than
        the window contains must still land on the SAME date the real
        calendar would give -- correctness must never depend on the
        window being wide enough."""
        real = services["work_calendar_engine"]
        window_start = date(2026, 1, 1)
        window_end = date(2026, 1, 10)  # deliberately narrow
        cached = MemoizingCalendarWindow(real, window_start, window_end)

        start, n = date(2026, 1, 5), 30  # walk far past window_end
        assert cached.add_working_days(start, n) == real.add_working_days(start, n)

    def test_next_working_day_matches(self, services):
        real = services["work_calendar_engine"]
        cached = MemoizingCalendarWindow(real, date(2026, 1, 1), date(2026, 3, 31))
        for d in [date(2026, 1, 3), date(2026, 1, 10)]:
            assert cached.next_working_day(d) == real.next_working_day(d)
            assert cached.next_working_day(d, include_today=False) == real.next_working_day(d, include_today=False)


class TestBuildMemoizingWindowForTasks:
    def test_window_covers_all_known_task_dates_with_padding(self, services):
        tasks = {
            "a": Task(id="a", project_id="p", name="Task A", duration_days=2, start_date=date(2026, 1, 5)),
            "b": Task(id="b", project_id="p", name="Task B", duration_days=2, start_date=date(2026, 6, 1)),
        }
        window = build_memoizing_window_for_tasks(
            services["work_calendar_engine"], tasks, search_horizon_working_days=60
        )
        assert window._window_start <= date(2026, 1, 5)
        assert window._window_end >= date(2026, 6, 1)

    def test_empty_tasks_still_produces_a_usable_window(self, services):
        window = build_memoizing_window_for_tasks(
            services["work_calendar_engine"], {}, search_horizon_working_days=60
        )
        assert window._window_start <= window._window_end
