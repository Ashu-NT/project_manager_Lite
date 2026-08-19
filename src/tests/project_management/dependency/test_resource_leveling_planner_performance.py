"""R4.4W/R4.4W.1 -- performance characterization for
ResourceLevelingPlanner at 100/1000/5000 tasks. Pure in-memory (no DB),
isolating the planner's own algorithmic cost from persistence/ORM
overhead -- the planner's public signature takes plain dicts/lists
regardless of where they came from, so this is a faithful measurement
of the same code path the desktop API drives.

R4.4W's original characterization found 111.2s at 5000 tasks (this
same scenario). Profiling (R4.4W.1) traced it to run_cpm's canonical
build_schedule_result calling calendar.working_days_between once per
task, uncached -- NOT to the planner calling run_cpm too many times
(only ~7 calls happen regardless of scale). The fix
(calendar_cache.MemoizingCalendarWindow, wired into
ResourceLevelingPlanner.build_proposal) bulk-resolves working-day facts
once per Preview instead of once per task. After the fix, this exact
scenario: 100 tasks 0.032s, 1000 tasks 0.341s, 5000 tasks 1.737s -- a
64x speedup at 5000 tasks, and scaling is now roughly linear rather
than quadratic. See test_zzz_profile_scratch.py (throwaway) and
test_leveling_calendar_cache.py (permanent correctness coverage) for
the profiling evidence and cache-correctness proof respectively; see
R4_4_PLANNING_SCHEDULING_IMPLEMENTATION_SUMMARY.md §R4.4W.1 for the
full before/after writeup.

Not a strict pass/fail gate (machine speed varies) -- these assertions
are generous upper bounds (still ~5-10x the observed numbers above);
the actual measured numbers are what matter for documentation, printed
via `-s`.
"""
from __future__ import annotations

import time
from datetime import date, timedelta

import pytest

from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment
from src.core.modules.project_management.application.scheduling.leveling.resource_leveling_planner import (
    ResourceLevelingPlanner,
)


class _MonToFriCalendar:
    def is_working_day(self, target_date: date) -> bool:
        return target_date.weekday() < 5

    def next_working_day(self, target_date: date, include_today: bool = True) -> date:
        current = target_date if include_today else target_date + timedelta(days=1)
        while not self.is_working_day(current):
            current += timedelta(days=1)
        return current

    def add_working_days(self, start: date, working_days: int) -> date:
        current = start
        step = 1 if working_days >= 0 else -1
        remaining = abs(working_days)
        while remaining > 0:
            current += timedelta(days=step)
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

    def working_day_dates_between(self, start: date, end: date) -> frozenset[date]:
        # Same day-by-day authority as working_days_between/is_working_day
        # above -- just returning the actual dates instead of a count, so
        # MemoizingCalendarWindow's bulk pre-fetch can build its cache from
        # this fake the same way it would from a real production calendar.
        if end < start:
            return frozenset()
        working: set[date] = set()
        current = start
        while current <= end:
            if self.is_working_day(current):
                working.add(current)
            current += timedelta(days=1)
        return frozenset(working)


def _build_project(task_count: int, calendar: _MonToFriCalendar):
    """`task_count` independent, non-overlapping tasks, EXCEPT tasks 0
    and 1 which intentionally share a resource on the same days --
    exactly one real conflict regardless of how large the project is,
    so timing reflects the cost of running the leveling search over an
    N-task graph, not the cost of resolving more conflicts."""
    tasks_by_id: dict[str, Task] = {}
    assignments: list[TaskAssignment] = []
    base = date(2026, 1, 5)  # a Monday
    for i in range(task_count):
        start = base if i in (0, 1) else calendar.add_working_days(base, i + 5)
        task_id = f"t{i}"
        tasks_by_id[task_id] = Task(
            id=task_id, project_id="perf", name=f"Task {i}", duration_days=2, start_date=start
        )
        resource_id = "shared" if i in (0, 1) else f"solo-{i}"
        assignments.append(
            TaskAssignment(id=f"a{i}", task_id=task_id, resource_id=resource_id, allocation_percent=70.0)
        )
    resource_name_by_id = {"shared": "Shared Dev"}
    return tasks_by_id, assignments, resource_name_by_id


@pytest.mark.parametrize("task_count,max_seconds", [(100, 1.0), (1000, 3.0), (5000, 10.0)])
def test_leveling_planner_scales_acceptably(task_count, max_seconds):
    calendar = _MonToFriCalendar()
    tasks_by_id, assignments, resource_name_by_id = _build_project(task_count, calendar)
    planner = ResourceLevelingPlanner(calendar)

    started = time.perf_counter()
    proposal = planner.build_proposal(
        project_id="perf",
        tasks_by_id=tasks_by_id,
        deps=[],
        assignments=assignments,
        resource_name_by_id=resource_name_by_id,
    )
    elapsed = time.perf_counter() - started

    print(f"\n[R4.4W] task_count={task_count} elapsed={elapsed:.3f}s moves={len(proposal.moves)}")

    assert proposal.resource_conflicts_after == 0
    assert len(proposal.moves) == 1
    assert elapsed < max_seconds, (
        f"ResourceLevelingPlanner took {elapsed:.2f}s for {task_count} tasks "
        f"(budget {max_seconds}s) -- investigate before this ships at scale."
    )
