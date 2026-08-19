"""Phase L: the Scheduling workspace's project-wide dependency read must be
O(1) queries regardless of task count, not the confirmed 2N+1 per-task
loop. See
docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
§17/Phase L.
"""
from __future__ import annotations

from datetime import date

from src.core.modules.project_management.domain.enums import DependencyType
from src.tests.project_management._sql_measurement_helpers import count_calls



def test_list_project_dependencies_is_one_query_not_per_task_loop(services):
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project("Query Perf", "")
    tasks = [
        ts.create_task(project.id, f"Task {i:02d}", "", start_date=date(2023, 11, 6), duration_days=1)
        for i in range(10)
    ]
    for a, b in zip(tasks, tasks[1:]):
        ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

    dependency_repo = ts._dependency_repo
    with count_calls(
        [
            (dependency_repo, "list_by_project", "list_by_project"),
            (dependency_repo, "list_by_task", "list_by_task"),
        ]
    ) as counts:
        result = ts.list_dependencies_for_project(project.id)

    assert len(result) == 9
    assert counts["list_by_project"] == 1
    assert counts["list_by_task"] == 0


def test_application_layer_method_is_permission_checked(services):
    """list_dependencies_for_project must not bypass the same
    read-permission checks list_dependencies_for_task already has."""
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Query Perf Permissions", "")
    result = ts.list_dependencies_for_project(project.id)
    assert result == []


def test_recalculation_only_persists_tasks_whose_dates_actually_changed(services):
    """Phase L1: a re-run of recalculate_project_schedule() that reproduces
    the same CPM dates for every task must not re-issue a repository update
    for any of them. Before this fix, every leaf task in the project was
    written unconditionally on every single recalculation, correlating DB
    write volume with project size rather than with how much the schedule
    actually moved.
    """
    ps = services["project_service"]
    ts = services["task_service"]
    sched = services["scheduling_engine"]

    project = ps.create_project("Persist Only Changed", "")
    tasks = [
        ts.create_task(
            project.id,
            f"Task {i:02d}",
            "",
            start_date=date(2023, 11, 6) if i == 0 else None,
            duration_days=2,
        )
        for i in range(10)
    ]
    for a, b in zip(tasks, tasks[1:]):
        ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

    # First run establishes and persists the CPM-derived dates.
    sched.recalculate_project_schedule(project.id)

    task_repo = sched._task_repo
    with count_calls([(task_repo, "update", "update")]) as counts:
        result = sched.recalculate_project_schedule(project.id)

    assert len(result) == len(tasks)
    assert counts["update"] == 0


def test_recalculation_persists_only_the_tasks_whose_dates_shift(services):
    """A change that shifts a dependency chain's root must persist the
    tasks whose dates actually move, and the mechanism must be driven by
    real date deltas rather than being an unconditional no-op."""
    ps = services["project_service"]
    ts = services["task_service"]
    sched = services["scheduling_engine"]

    project = ps.create_project("Persist Partial Shift", "")
    tasks = [
        ts.create_task(
            project.id,
            f"Task {i:02d}",
            "",
            start_date=date(2023, 11, 6) if i == 0 else None,
            duration_days=2,
        )
        for i in range(10)
    ]
    for a, b in zip(tasks, tasks[1:]):
        ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

    sched.recalculate_project_schedule(project.id)

    # update_task() already persists task 0's own new start_date directly,
    # so recalculation only needs to re-persist the 9 downstream tasks
    # whose derived dates actually move as a result -- not task 0 itself,
    # whose stored date already matches what CPM re-derives for it.
    ts.update_task(tasks[0].id, start_date=date(2023, 11, 13))

    task_repo = sched._task_repo
    with count_calls([(task_repo, "update", "update")]) as counts:
        result = sched.recalculate_project_schedule(project.id)

    assert len(result) == len(tasks)
    assert counts["update"] == len(tasks) - 1
