"""Phase J: actual-date x dependency semantics.

Characterizes and pins the existing behavior (actuals are historical
truth, never moved to satisfy a planned dependency; a predecessor's actual
dates propagate to successors; a task's own actual date can only float the
computed date later via the one-sided floor, never earlier) and adds the
previously-missing signal: an explicit, non-blocking fact when a task's
own actual execution violated what its dependency graph required. See
docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
§14/Phase J.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta

import pytest

from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency
from src.core.modules.project_management.application.scheduling.cpm.pure_cpm import run_cpm
from src.core.modules.project_management.application.scheduling.cpm.dependency_actual_variance import (
    find_dependency_actual_variances,
)


class MonToFriCalendar:
    def is_working_day(self, target_date: date) -> bool:
        return target_date.weekday() < 5

    def next_working_day(self, target_date: date, include_today: bool = True) -> date:
        current = target_date if include_today else target_date + timedelta(days=1)
        while not self.is_working_day(current):
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
        lo, hi = (start, end) if start <= end else (end, start)
        return sum(1 for i in range((hi - lo).days + 1) if self.is_working_day(lo + timedelta(days=i)))


CAL = MonToFriCalendar()
MON = date(2023, 11, 6)


class TestPredecessorActualPropagation:
    """Predecessor actuals are historical truth and DRIVE the successor --
    already-correct existing behavior, pinned here."""

    def test_predecessor_actual_end_drives_fs_successor(self):
        a = Task.create("p1", "Task A", start_date=MON, duration_days=3)
        b = Task.create("p1", "Task B", duration_days=2)
        dep = TaskDependency.create(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

        planned_a_finish = run_cpm(CAL, {a.id: a, b.id: b}, [dep]).schedule[a.id].earliest_finish

        # A actually finished 2 working days LATER than planned.
        a_late = replace(a, actual_start=MON, actual_end=CAL.add_working_days(planned_a_finish, 3))
        result = run_cpm(CAL, {a.id: a_late, b.id: b}, [dep])

        expected_b_start = CAL.next_working_day(a_late.actual_end, include_today=False)
        assert result.schedule[b.id].earliest_start == expected_b_start

    def test_predecessor_actual_start_drives_ss_successor(self):
        a = Task.create("p1", "Task A", start_date=MON, duration_days=3)
        b = Task.create("p1", "Task B", duration_days=2)
        dep = TaskDependency.create(a.id, b.id, DependencyType.START_TO_START, lag_days=0)

        # A actually started 2 working days later than planned.
        a_late_start = CAL.add_working_days(MON, 2)
        a_late = replace(a, actual_start=a_late_start)
        result = run_cpm(CAL, {a.id: a_late, b.id: b}, [dep])

        assert result.schedule[b.id].earliest_start == a_late_start


class TestOwnActualIsAOneSidedFloorNeverEarlier:
    """A task's own actual_start can only push its computed start LATER
    (floor), never earlier -- confirmed unchanged, pinned here."""

    def test_actual_start_earlier_than_dependency_is_not_applied(self):
        a = Task.create("p1", "Task A", start_date=MON, duration_days=3)
        b = Task.create(
            "p1", "Task B", duration_days=2,
            actual_start=date(2023, 11, 1),  # earlier than what FS would require
        )
        dep = TaskDependency.create(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

        result = run_cpm(CAL, {a.id: a, b.id: b}, [dep])
        b_info = result.schedule[b.id]

        dependency_required = CAL.next_working_day(result.schedule[a.id].earliest_finish, include_today=False)
        # The earlier actual_start is NOT applied -- the dependency-derived
        # date wins on the committed schedule (one-sided floor).
        assert b_info.earliest_start == dependency_required
        assert b_info.earliest_start != date(2023, 11, 1)


class TestDependencyActualVarianceReporting:
    """The previously-missing signal: an explicit fact when a task's own
    actual date violated what its dependency graph required."""

    def test_successor_actual_start_earlier_than_required_is_reported(self):
        a = Task.create("p1", "Task A", start_date=MON, duration_days=3)
        b = Task.create(
            "p1", "Task B", duration_days=2,
            actual_start=date(2023, 11, 1),  # started before A's plan permits
        )
        dep = TaskDependency.create(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

        result = run_cpm(CAL, {a.id: a, b.id: b}, [dep])
        variances = find_dependency_actual_variances({a.id: a, b.id: b}, result.schedule, CAL)

        assert len(variances) == 1
        v = variances[0]
        assert v.task_id == b.id
        assert v.direction == "start"
        assert v.actual_date == date(2023, 11, 1)
        assert v.code == "DEPENDENCY_ACTUAL_VARIANCE"
        assert v.difference_working_days > 0

    def test_no_variance_when_actual_matches_or_exceeds_requirement(self):
        a = Task.create("p1", "Task A", start_date=MON, duration_days=3)
        dependency_required = CAL.next_working_day(CAL.add_working_days(MON, 3), include_today=False)
        b = Task.create("p1", "Task B", duration_days=2, actual_start=dependency_required)
        dep = TaskDependency.create(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

        result = run_cpm(CAL, {a.id: a, b.id: b}, [dep])
        variances = find_dependency_actual_variances({a.id: a, b.id: b}, result.schedule, CAL)
        assert variances == []

    def test_no_variance_reported_for_task_with_no_incoming_dependency(self):
        a = Task.create("p1", "Task A", start_date=MON, duration_days=2, actual_start=date(2023, 11, 1))
        result = run_cpm(CAL, {a.id: a}, [])
        variances = find_dependency_actual_variances({a.id: a}, result.schedule, CAL)
        assert variances == []

    def test_successor_actual_finish_earlier_than_ff_requirement_is_reported(self):
        a = Task.create("p1", "Task A", start_date=MON, duration_days=3)
        b = Task.create(
            "p1", "Task B", duration_days=2,
            actual_start=date(2023, 10, 23),
            actual_end=date(2023, 10, 25),  # finished before A's FF plan permits
        )
        dep = TaskDependency.create(a.id, b.id, DependencyType.FINISH_TO_FINISH, lag_days=0)

        result = run_cpm(CAL, {a.id: a, b.id: b}, [dep])
        variances = find_dependency_actual_variances({a.id: a, b.id: b}, result.schedule, CAL)

        # For a duration-bearing task, the dependency-implied start and
        # finish are linked by duration, so a task whose actual dates fall
        # well short of an FF requirement can legitimately trip both the
        # "start" and "finish" comparisons at once -- assert the "finish"
        # one this test targets is present, without assuming it's the only
        # one.
        by_direction = {v.direction: v for v in variances}
        assert "finish" in by_direction
        assert by_direction["finish"].task_id == b.id
        assert by_direction["finish"].actual_date == date(2023, 10, 25)
