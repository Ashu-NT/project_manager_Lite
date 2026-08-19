"""RESOLVED (R4.4 constraint-aware backward CPM pass): backward-pass
constraint/float blindness, originally characterized and deliberately
NOT implemented in the R4.4 constraint feature pass (see git history for
this file's prior content), is now fixed. Kept as a regression file --
not renamed -- so a future change accidentally regressing this cannot
land without touching a test file whose name still describes exactly
the risk being guarded against.

backward CPM" section. Summary:

- MUST_START_ON / MUST_FINISH_ON (exact pins): own total float is 0 --
  the task cannot move regardless of what slack the network would
  otherwise allow. Propagates backward to predecessors like any other
  successor-derived bound.
- START_NO_EARLIER_THAN / FINISH_NO_EARLIER_THAN (floors): unchanged --
  already correct via the raised forward-pass est/eft.
- START_NO_LATER_THAN / FINISH_NO_LATER_THAN (ceilings): cap the task's
  own late date at the constraint date, which can legitimately drive
  total float NEGATIVE when the dependency-required date already
  exceeds the ceiling -- reported as a true negative magnitude, never
  clamped to 0 (see results.py), plus a new CPMTaskInfo.is_infeasible
  flag.
- DEADLINE: same ceiling treatment as FINISH_NO_LATER_THAN, but reads
  task.deadline instead of constraint_date -- and never becomes a
  scheduling constraint in its own right.
"""
from __future__ import annotations

from datetime import date, timedelta

from src.core.modules.project_management.domain.enums import ConstraintType, DependencyType
from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency
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
            return 0  # matches every production CalendarProtocol implementation
        count = 0
        current = start
        while current <= end:
            if self.is_working_day(current):
                count += 1
            current += timedelta(days=1)
        return count


def test_a_must_start_on_pinned_task_now_reports_zero_total_float():
    calendar = _MonToFriCalendar()
    task = Task(
        id="pinned",
        project_id="p1",
        name="Pinned Task",
        duration_days=3,
        constraint_type=ConstraintType.MUST_START_ON,
        constraint_date=date(2026, 9, 7),  # a Monday
    )
    result = run_cpm(calendar, {"pinned": task}, [])
    info = result.schedule["pinned"]

    assert info.earliest_start == date(2026, 9, 7)
    assert info.latest_start == info.earliest_start
    assert info.latest_finish == info.earliest_finish
    assert info.total_float_days == 0
    assert info.is_critical is True
    assert info.is_infeasible is False


def test_a_must_start_on_pin_now_propagates_backward_through_a_real_successor():
    """
    Correcting a flawed premise in the original (never-implemented)
    decision record: an exact pin on B does NOT force a's float to 0 --
    MUST_START_ON fixes B's start at an exact date, it does not turn the
    A--FS-->B edge into an exact-pin relationship. A only needs to
    finish EARLY ENOUGH (on or before one working day before B's pinned
    start) for the FS relationship to hold; consistent with that, A
    legitimately has slack across that whole window. What the fix must
    prove is that A's latest start/finish are now derived from B's
    ACTUAL pinned position (2026-09-21), not from C's far-later position
    (2026-10-05) the way the pre-fix bug would have propagated."""
    calendar = _MonToFriCalendar()
    a = Task(id="a", project_id="p1", name="Task A", duration_days=2, start_date=date(2026, 9, 7))
    b = Task(
        id="b",
        project_id="p1",
        name="Task B",
        duration_days=2,
        constraint_type=ConstraintType.MUST_START_ON,
        # Far later than A --FS--> B alone implies (A finishes 2026-09-08).
        constraint_date=date(2026, 9, 21),
    )
    c = Task(id="c", project_id="p1", name="Task C", duration_days=2, start_date=date(2026, 10, 5))
    dep_ab = TaskDependency.create(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
    dep_bc = TaskDependency.create(b.id, c.id, DependencyType.FINISH_TO_START, lag_days=0)
    result = run_cpm(calendar, {"a": a, "b": b, "c": c}, [dep_ab, dep_bc])

    info_a = result.schedule["a"]
    info_b = result.schedule["b"]
    assert info_b.earliest_start == date(2026, 9, 21)  # MSO override confirmed to have fired

    # B is pinned -- it cannot move, regardless of the slack C's late
    # start would otherwise offer it.
    assert info_b.total_float_days == 0
    assert info_b.is_critical is True

    # A's latest start/finish are now one working day before B's PIN
    # (2026-09-18 latest finish, 2026-09-17 latest start) -- derived from
    # B's actual fixed position, not from C's far-later slack. Before
    # this fix, B's own late date leaked through from C (project finish
    # 2026-10-07), which would have put A's latest start weeks later
    # than this.
    assert info_a.latest_finish == date(2026, 9, 18)
    assert info_a.latest_start == date(2026, 9, 17)
    assert info_a.total_float_days == 8
    assert info_a.is_critical is False


def test_a_must_finish_on_pin_gives_the_task_zero_own_float():
    calendar = _MonToFriCalendar()
    task = Task(
        id="pinned",
        project_id="p1",
        name="Pinned Finish",
        duration_days=3,
        constraint_type=ConstraintType.MUST_FINISH_ON,
        constraint_date=date(2026, 9, 9),  # a Wednesday
    )
    result = run_cpm(calendar, {"pinned": task}, [])
    info = result.schedule["pinned"]

    assert info.earliest_finish == date(2026, 9, 9)
    assert info.latest_start == info.earliest_start
    assert info.latest_finish == info.earliest_finish
    assert info.total_float_days == 0


def test_start_no_later_than_ceiling_infeasible_against_a_dependency_reports_negative_float():
    """Standalone A --FS--> B, B has an SNLT ceiling that the
    dependency-implied start already exceeds -- genuinely infeasible,
    not merely tight, and must be reported as such (never clamped to
    0)."""
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

    assert info_b.earliest_start == date(2026, 9, 11)
    assert info_b.latest_start == date(2026, 9, 8)
    assert info_b.total_float_days < 0
    assert info_b.is_infeasible is True
    assert info_b.is_critical is True


def test_finish_no_later_than_ceiling_infeasible_reports_negative_float():
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
    info_b = result.schedule["b"]

    assert info_b.total_float_days < 0
    assert info_b.is_infeasible is True


def test_start_no_later_than_ceiling_satisfied_reports_ordinary_nonnegative_float():
    """A satisfied ceiling (network-implied date already within the
    ceiling) must NOT be reported as infeasible -- only a genuine
    incompatibility flips is_infeasible."""
    calendar = _MonToFriCalendar()
    task = Task(
        id="solo",
        project_id="p1",
        name="Solo",
        duration_days=2,
        start_date=date(2026, 9, 7),
        constraint_type=ConstraintType.START_NO_LATER_THAN,
        constraint_date=date(2026, 9, 30),  # far in the future -- easily satisfied
    )
    result = run_cpm(calendar, {"solo": task}, [])
    info = result.schedule["solo"]

    assert info.total_float_days is not None and info.total_float_days >= 0
    assert info.is_infeasible is False
