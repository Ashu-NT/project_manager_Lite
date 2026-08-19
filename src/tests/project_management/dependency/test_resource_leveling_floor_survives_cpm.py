"""R4.4C -- the leveled-schedule model. Proves the new
Task.resource_leveling_not_before floor solves the exact defect pinned
by test_leveling_dependency_boundary.py: a resource-leveling decision
must survive every subsequent canonical run_cpm call, even for a task
with an incoming dependency (which run_cpm's forward pass otherwise
ignores Task.start_date for entirely).

This file tests the DOMAIN/CPM MECHANISM in isolation (pure_cpm.run_cpm)
-- not yet the actual leveling engine, which is migrated separately
(R4.4B/J/K/M) to WRITE this field instead of raw start_date. See
test_leveling_dependency_boundary.py for the still-pinned proof that the
OLD write-raw-start_date behavior is broken; this file proves the NEW
mechanism the migrated engine will rely on is sound.
"""
from __future__ import annotations

from datetime import date, timedelta

from src.core.modules.project_management.domain.enums import DependencyType
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
            return 0
        count = 0
        current = start
        while current <= end:
            if self.is_working_day(current):
                count += 1
            current += timedelta(days=1)
        return count


def _fs(pred: Task, succ: Task, lag_days: int = 0) -> TaskDependency:
    return TaskDependency.create(pred.id, succ.id, DependencyType.FINISH_TO_START, lag_days=lag_days)


def test_leveling_floor_survives_repeated_cpm_runs_on_a_dependency_linked_task():
    """The exact scenario test_leveling_dependency_boundary.py pins as
    broken, reproduced with the NEW mechanism: Task B has an incoming
    FS dependency from Task A (so run_cpm would otherwise recompute its
    start purely from the dependency graph, ignoring start_date
    entirely) AND a resource_leveling_not_before floor set later than
    the dependency-implied date. The floor must win, and must keep
    winning across repeated run_cpm calls -- not just the first one."""
    calendar = _MonToFriCalendar()
    a = Task(id="a", project_id="p1", name="Task A", duration_days=2, start_date=date(2026, 9, 7))
    b = Task(
        id="b", project_id="p1", name="Task B", duration_days=2,
        resource_leveling_not_before=date(2026, 9, 21),  # well past the FS-implied start
    )
    dep = _fs(a, b)

    result_1 = run_cpm(calendar, {"a": a, "b": b}, [dep])
    info_b_1 = result_1.schedule["b"]
    assert info_b_1.earliest_start == date(2026, 9, 21)

    # Re-run CPM again with the SAME persisted floor still in place (as a
    # real repository round-trip would leave it) -- the floor must win
    # AGAIN, not just once. This is the exact repeated-recalculation
    # scenario that erased the old raw-start_date write.
    result_2 = run_cpm(calendar, {"a": a, "b": b}, [dep])
    info_b_2 = result_2.schedule["b"]
    assert info_b_2.earliest_start == date(2026, 9, 21)


def test_leveling_floor_composes_with_dependency_when_dependency_is_later():
    """If the dependency-implied date is LATER than the leveling floor,
    the dependency wins (the floor is a minimum, not a fixed point) --
    leveling only ever pushes a task LATER than it would otherwise be,
    never earlier than the network requires."""
    calendar = _MonToFriCalendar()
    a = Task(id="a", project_id="p1", name="Task A", duration_days=10, start_date=date(2026, 9, 7))
    b = Task(
        id="b", project_id="p1", name="Task B", duration_days=2,
        resource_leveling_not_before=date(2026, 9, 8),  # earlier than the FS-implied start
    )
    dep = _fs(a, b)

    result = run_cpm(calendar, {"a": a, "b": b}, [dep])
    info_b = result.schedule["b"]

    assert info_b.earliest_start > date(2026, 9, 8)  # dependency wins, not the floor


def test_leveling_floor_ignored_once_task_is_completed():
    """A completed task's actual dates are historical truth -- a
    leveling floor recorded before completion must never resurrect
    itself over the real, already-happened dates."""
    calendar = _MonToFriCalendar()
    task = Task(
        id="a", project_id="p1", name="Task A", duration_days=2,
        actual_start=date(2026, 9, 7), actual_end=date(2026, 9, 9),
        resource_leveling_not_before=date(2026, 9, 21),
    )
    result = run_cpm(calendar, {"a": task}, [])
    info = result.schedule["a"]

    assert info.earliest_start == date(2026, 9, 7)
    assert info.earliest_finish == date(2026, 9, 9)


def test_no_leveling_floor_is_a_no_op():
    calendar = _MonToFriCalendar()
    task = Task(id="a", project_id="p1", name="Task A", duration_days=2, start_date=date(2026, 9, 7))
    result = run_cpm(calendar, {"a": task}, [])
    info = result.schedule["a"]

    assert info.earliest_start == date(2026, 9, 7)


def test_leveling_floor_survives_the_live_persisting_scheduling_engine_too(services):
    """The same mechanism must hold through SchedulingEngine.
    recalculate_project_schedule -- the LIVE, persisting path
    DashboardService/leveling actually calls (per R4.4A verification,
    pure_cpm.run_cpm and SchedulingEngine have separate orchestrations
    sharing the same primitives; both must apply this floor)."""
    ps = services["project_service"]
    ts = services["task_service"]
    sched = services["scheduling_engine"]

    project = ps.create_project("Leveling Floor Survives Live Engine", "")
    task_a = ts.create_task(project.id, "Task A", "", start_date=date(2026, 9, 7), duration_days=2)
    task_b = ts.create_task(project.id, "Task B", "", duration_days=2)
    ts.add_dependency(
        predecessor_id=task_a.id,
        successor_id=task_b.id,
        dependency_type=DependencyType.FINISH_TO_START,
        lag_days=0,
    )

    task_b_raw = ts._task_repo.get(task_b.id)
    from dataclasses import replace

    task_b_floored = replace(task_b_raw, resource_leveling_not_before=date(2026, 9, 21))
    ts._task_repo.update(task_b_floored)
    ts._session.commit()

    sched.recalculate_project_schedule(project.id)
    assert ts.get_task(task_b.id).start_date == date(2026, 9, 21)

    # Repeat -- must still hold, not just on the first recalculation.
    sched.recalculate_project_schedule(project.id)
    assert ts.get_task(task_b.id).start_date == date(2026, 9, 21)
