"""Task Detail -> Schedule Impact: current-state schedule facts.

Integration-style (real services/calendar, not a hand-rolled calendar
fake) to match this test package's established convention. Exercises the
orchestration in
application/scheduling/forecasting/task_schedule_overview.py directly
against a real run_cpm result -- no new scheduling math under test here,
only the free-float/downstream-exposure/drivers orchestration built on
top of it.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.core.modules.project_management.application.scheduling.cpm.pure_cpm import run_cpm
from src.core.modules.project_management.application.scheduling.forecasting.task_schedule_overview import (
    build_schedule_drivers,
    build_successors_by_task_id,
    compute_downstream_exposure,
    compute_free_float_days,
)
from src.core.modules.project_management.domain.enums import DependencyType


def _run_cpm_for_project(services, project_id):
    ts = services["task_service"]
    wc = services["work_calendar_engine"]
    tasks = ts.list_tasks_for_project(project_id)
    tasks_by_id = {t.id: t for t in tasks}
    deps = []
    for t in tasks:
        deps.extend(ts.list_dependencies_for_task(t.id))
    # de-dupe (each edge appears once per endpoint's list_dependencies_for_task)
    deps_by_id = {d.id: d for d in deps}
    deps = list(deps_by_id.values())
    result = run_cpm(wc, tasks_by_id, deps)
    return tasks_by_id, deps, result


def test_free_float_equals_total_float_for_a_task_with_no_successors(services):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Schedule Overview Free Float", "")
    task = ts.create_task(project.id, "Leaf", "", start_date=date(2024, 1, 1), duration_days=2)

    tasks_by_id, deps, result = _run_cpm_for_project(services, project.id)

    free_float = compute_free_float_days(task.id, result.schedule, deps, services["work_calendar_engine"])
    assert free_float == result.schedule[task.id].total_float_days


def test_free_float_is_computed_for_an_fs_successor_chain(services):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Schedule Overview FS Free Float", "")
    a = ts.create_task(project.id, "Task A", "", start_date=date(2024, 1, 1), duration_days=2)
    b = ts.create_task(project.id, "Task B", "", duration_days=2)
    ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

    tasks_by_id, deps, result = _run_cpm_for_project(services, project.id)

    free_float = compute_free_float_days(a.id, result.schedule, deps, services["work_calendar_engine"])
    # A's only successor (B) has no float of its own relative to A here,
    # since nothing else constrains B later -- A's free float is 0 because
    # B's earliest start is exactly the working day after A finishes.
    assert free_float == 0


def test_free_float_is_unavailable_for_a_non_fs_successor(services):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Schedule Overview Non-FS Free Float", "")
    a = ts.create_task(project.id, "Task A", "", start_date=date(2024, 1, 1), duration_days=2)
    b = ts.create_task(project.id, "Task B", "", duration_days=2)
    ts.add_dependency(a.id, b.id, DependencyType.START_TO_START, lag_days=0)

    tasks_by_id, deps, result = _run_cpm_for_project(services, project.id)

    free_float = compute_free_float_days(a.id, result.schedule, deps, services["work_calendar_engine"])
    assert free_float is None


def test_downstream_exposure_counts_transitive_tasks_and_milestones(services):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Schedule Overview Downstream", "")
    a = ts.create_task(project.id, "Task A", "", start_date=date(2024, 1, 1), duration_days=2)
    b = ts.create_task(project.id, "Task B", "", duration_days=2)
    c = ts.create_task(project.id, "Task C", "", duration_days=2)
    milestone = ts.create_task(project.id, "Milestone", "", duration_days=0)
    unrelated = ts.create_task(project.id, "Unrelated", "", start_date=date(2024, 1, 1), duration_days=1)

    ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
    ts.add_dependency(b.id, c.id, DependencyType.FINISH_TO_START, lag_days=0)
    ts.add_dependency(c.id, milestone.id, DependencyType.FINISH_TO_START, lag_days=0)

    tasks_by_id, deps, result = _run_cpm_for_project(services, project.id)
    successors = build_successors_by_task_id(deps)
    critical_ids = set(result.critical_path_task_ids)

    exposure = compute_downstream_exposure(a.id, tasks_by_id, successors, critical_ids)

    assert exposure.direct_successor_count == 1
    assert exposure.downstream_task_count == 3  # b, c, milestone -- not "unrelated"
    assert exposure.downstream_milestone_count == 1
    assert unrelated.id not in {b.id, c.id, milestone.id}


def test_downstream_exposure_is_zero_for_a_leaf_task(services):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Schedule Overview Downstream Leaf", "")
    task = ts.create_task(project.id, "Leaf", "", start_date=date(2024, 1, 1), duration_days=1)

    tasks_by_id, deps, result = _run_cpm_for_project(services, project.id)
    successors = build_successors_by_task_id(deps)

    exposure = compute_downstream_exposure(task.id, tasks_by_id, successors, set(result.critical_path_task_ids))

    assert exposure.direct_successor_count == 0
    assert exposure.downstream_task_count == 0
    assert exposure.downstream_milestone_count == 0
    assert exposure.critical_downstream_count == 0


def test_schedule_drivers_list_every_incoming_dependency_and_constraint_and_actuals(services):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Schedule Overview Drivers", "")
    a = ts.create_task(project.id, "Foundation Complete", "", start_date=date(2024, 1, 1), duration_days=2)
    b = ts.create_task(project.id, "Electrical", "", duration_days=2)
    ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=2)

    b_reloaded = next(t for t in ts.list_tasks_for_project(project.id) if t.id == b.id)
    b_with_actual = replace(b_reloaded, actual_start=date(2024, 1, 8))
    incoming = [d for d in ts.list_dependencies_for_task(b.id) if d.successor_task_id == b.id]

    drivers = build_schedule_drivers(b_with_actual, incoming, {a.id: a.name})

    kinds = {d.kind for d in drivers}
    assert "predecessor" in kinds
    assert "actual_start" in kinds
    predecessor_driver = next(d for d in drivers if d.kind == "predecessor")
    assert predecessor_driver.label == "Foundation Complete"
    assert "FS" in predecessor_driver.detail
    assert "+2d" in predecessor_driver.detail


def test_schedule_drivers_is_empty_for_a_task_with_no_facts(services):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Schedule Overview No Drivers", "")
    task = ts.create_task(project.id, "Untouched", "", start_date=date(2024, 1, 1), duration_days=1)

    drivers = build_schedule_drivers(task, [], {})

    assert drivers == ()
