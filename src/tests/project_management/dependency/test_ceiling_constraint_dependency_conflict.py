"""Phase K (R4.4 constraint pass): SNLT/FNLT dependency infeasibility.
Extends DependencyConstraintConflict (previously MSO/MFO-only) to also
cover START_NO_LATER_THAN/FINISH_NO_LATER_THAN -- these never drive the
forward pass, so a dependency-implied date past the ceiling flows
through untouched and needs its own conflict fact carrying the
dependency context, distinct from the plain ConstraintViolation
_check_task already reports for the same situation.
"""
from __future__ import annotations

from datetime import date, timedelta

from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency
from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import (
    ConstraintType,
    ConstraintValidator,
)
from src.core.modules.project_management.application.scheduling.cpm.pure_cpm import run_cpm


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
            return -self.working_days_between(end, start)
        count = 0
        current = start
        while current <= end:
            if self.is_working_day(current):
                count += 1
            current += timedelta(days=1)
        return count


def test_start_no_later_than_ceiling_infeasible_against_a_dependency_is_reported_as_a_conflict():
    calendar = _MonToFriCalendar()
    a = Task(id="a", project_id="p1", name="Task A", duration_days=3, start_date=date(2026, 9, 7))
    b = Task(
        id="b",
        project_id="p1",
        name="Task B",
        duration_days=2,
        constraint_type=ConstraintType.START_NO_LATER_THAN,
        # A --FS--> B implies B starts 2026-09-11; the ceiling forbids
        # starting any later than 2026-09-08 -- infeasible.
        constraint_date=date(2026, 9, 8),
    )
    dep = TaskDependency.create(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
    result = run_cpm(calendar, {"a": a, "b": b}, [dep])
    info_b = result.schedule["b"]

    # The ceiling never drives the schedule -- the dependency wins.
    assert info_b.earliest_start == date(2026, 9, 11)
    assert info_b.dependency_implied_start == date(2026, 9, 11)

    validator = ConstraintValidator(calendar)
    validation = validator.validate({"a": a, "b": b}, result.schedule)

    # The plain violation still fires (ceiling exceeded).
    assert any(v.constraint_type is ConstraintType.START_NO_LATER_THAN for v in validation.violations)

    # AND the new dependency-conflict fact carries the "why": which
    # predecessor relationship caused the infeasibility.
    conflicts = [c for c in validation.dependency_conflicts if c.task_id == "b"]
    assert len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict.constraint_type is ConstraintType.START_NO_LATER_THAN
    assert conflict.constraint_date == date(2026, 9, 8)
    assert conflict.dependency_required_date == date(2026, 9, 11)
    assert conflict.direction == "start"


def test_finish_no_later_than_ceiling_infeasible_against_a_dependency_is_reported_as_a_conflict():
    calendar = _MonToFriCalendar()
    a = Task(id="a", project_id="p1", name="Task A", duration_days=3, start_date=date(2026, 9, 7))
    b = Task(
        id="b",
        project_id="p1",
        name="Task B",
        duration_days=2,
        constraint_type=ConstraintType.FINISH_NO_LATER_THAN,
        constraint_date=date(2026, 9, 9),
    )
    dep = TaskDependency.create(a.id, b.id, DependencyType.FINISH_TO_FINISH, lag_days=0)
    result = run_cpm(calendar, {"a": a, "b": b}, [dep])

    validator = ConstraintValidator(calendar)
    validation = validator.validate({"a": a, "b": b}, result.schedule)
    conflicts = [c for c in validation.dependency_conflicts if c.task_id == "b"]
    assert len(conflicts) == 1
    assert conflicts[0].direction == "finish"


def test_start_no_later_than_ceiling_satisfied_by_a_dependency_reports_no_conflict():
    """No infeasibility when the dependency-implied date already
    satisfies the ceiling -- only a genuine incompatibility is reported,
    not every ceiling constraint that happens to coexist with a
    dependency."""
    calendar = _MonToFriCalendar()
    a = Task(id="a", project_id="p1", name="Task A", duration_days=1, start_date=date(2026, 9, 7))
    b = Task(
        id="b",
        project_id="p1",
        name="Task B",
        duration_days=2,
        constraint_type=ConstraintType.START_NO_LATER_THAN,
        constraint_date=date(2026, 9, 30),  # far in the future -- easily satisfied
    )
    dep = TaskDependency.create(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
    result = run_cpm(calendar, {"a": a, "b": b}, [dep])

    validator = ConstraintValidator(calendar)
    validation = validator.validate({"a": a, "b": b}, result.schedule)
    assert validation.is_valid
    assert [c for c in validation.dependency_conflicts if c.task_id == "b"] == []
