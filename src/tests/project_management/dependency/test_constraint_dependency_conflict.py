"""Phase F regression: hard constraints must not silently override a
dependency-driven date with no trace of the conflict. See
docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
§12/Phase F for the audit finding this closes.

Pure, in-memory tests (no DB) using ``run_cpm`` directly with hand-built
``Task``/``TaskDependency`` domain objects -- NOT the ``services`` fixture's
repository round-trip. This is deliberate: ``Task.constraint_type`` and
``Task.constraint_date`` were discovered, while building this test, to have
NO backing ORM columns at all (grep confirms zero references in
infrastructure/persistence/orm/task.py or mappers/task.py) -- they are
accepted at construction but silently dropped on every save/reload. That is
a real, separate backend gap (Task-level constraint persistence, not a
TaskDependency concern) that this pass does not fix; testing through the
repository would only produce false-positive passes (no constraint ever
actually reaching the engine). ``run_cpm`` exercises the exact same
``task_date_math``/``ConstraintValidator`` code SchedulingEngine uses
(Phase D consolidated them), so this is genuine coverage of the real
production logic, not a shortcut around it.
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
MON = date(2023, 11, 6)  # a Monday


def test_must_start_on_overriding_a_dependency_is_reported_as_a_conflict():
    """The audit's own worked example: A FS-> B, B has Must Start On set
    earlier than A's dependency-driven earliest start. The engine still
    honors the hard constraint (unchanged behavior), but the conflict must
    now be reported as an explicit fact, not silently swallowed."""
    a = Task.create("p1", "Task A", start_date=MON, duration_days=3)
    b = Task.create(
        "p1", "Task B", duration_days=2,
        constraint_type=ConstraintType.MUST_START_ON.value,
        constraint_date=date(2023, 11, 1),  # strictly before what FS would require
    )
    dep = TaskDependency.create(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

    result = run_cpm(CAL, {a.id: a, b.id: b}, [dep])
    b_info = result.schedule[b.id]
    a_info = result.schedule[a.id]

    # Unchanged behavior: the hard constraint still wins on the committed
    # schedule.
    assert b_info.earliest_start == date(2023, 11, 1)

    # New: the dependency-implied date (what FS alone required) is captured
    # and differs from what was actually scheduled.
    dependency_required_start = CAL.next_working_day(a_info.earliest_finish, include_today=False)
    assert b_info.dependency_implied_start == dependency_required_start
    assert b_info.dependency_implied_start != b_info.earliest_start

    validator = ConstraintValidator(calendar=CAL)
    validation = validator.validate({a.id: a, b.id: b}, result.schedule)

    assert len(validation.dependency_conflicts) == 1
    conflict = validation.dependency_conflicts[0]
    assert conflict.task_id == b.id
    assert conflict.code == "DEPENDENCY_CONSTRAINT_CONFLICT"
    assert conflict.constraint_type == ConstraintType.MUST_START_ON
    assert conflict.constraint_date == date(2023, 11, 1)
    assert conflict.dependency_required_date == dependency_required_start
    assert conflict.direction == "start"
    # Positive difference_working_days = the constraint pulled the task
    # EARLIER than the dependency required (dependency_required_date is
    # later than constraint_date).
    assert conflict.difference_working_days > 0


def test_must_finish_on_overriding_a_dependency_is_reported_as_a_conflict():
    a = Task.create("p1", "Task A", start_date=MON, duration_days=3)
    b = Task.create(
        "p1", "Task B", duration_days=2,
        constraint_type=ConstraintType.MUST_FINISH_ON.value,
        constraint_date=date(2023, 11, 1),
    )
    dep = TaskDependency.create(a.id, b.id, DependencyType.FINISH_TO_FINISH, lag_days=0)

    result = run_cpm(CAL, {a.id: a, b.id: b}, [dep])
    b_info = result.schedule[b.id]
    a_info = result.schedule[a.id]

    assert b_info.earliest_finish == date(2023, 11, 1)
    assert b_info.dependency_implied_finish == a_info.earliest_finish
    assert b_info.dependency_implied_finish != b_info.earliest_finish

    validator = ConstraintValidator(calendar=CAL)
    validation = validator.validate({a.id: a, b.id: b}, result.schedule)

    assert len(validation.dependency_conflicts) == 1
    conflict = validation.dependency_conflicts[0]
    assert conflict.direction == "finish"
    assert conflict.constraint_type == ConstraintType.MUST_FINISH_ON


def test_no_conflict_reported_when_constraint_matches_dependency():
    """No false positives: if the constraint date happens to equal what the
    dependency already required, there is no conflict to report."""
    a = Task.create("p1", "Task A", start_date=MON, duration_days=3)
    natural_start = CAL.next_working_day(CAL.add_working_days(MON, 3), include_today=False)
    b = Task.create(
        "p1", "Task B", duration_days=2,
        constraint_type=ConstraintType.MUST_START_ON.value,
        constraint_date=natural_start,
    )
    dep = TaskDependency.create(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

    result = run_cpm(CAL, {a.id: a, b.id: b}, [dep])
    validator = ConstraintValidator(calendar=CAL)
    validation = validator.validate({a.id: a, b.id: b}, result.schedule)

    assert validation.dependency_conflicts == []


def test_no_conflict_reported_when_task_has_no_incoming_dependency():
    """A constrained task with no incoming dependency has nothing to
    conflict with -- dependency_implied_start/finish stay None."""
    a = Task.create(
        "p1", "Task A", duration_days=2,
        constraint_type=ConstraintType.MUST_START_ON.value,
        constraint_date=MON,
    )
    result = run_cpm(CAL, {a.id: a}, [])

    assert result.schedule[a.id].dependency_implied_start is None
    assert result.schedule[a.id].dependency_implied_finish is None

    validator = ConstraintValidator(calendar=CAL)
    validation = validator.validate({a.id: a}, result.schedule)
    assert validation.dependency_conflicts == []
