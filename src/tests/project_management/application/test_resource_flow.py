from datetime import date

import pytest

from src.core.modules.project_management.application.tasks.commands import (
    assignment as assignment_commands,
)


def test_resource_assignment_and_overload(services):
    ps = services["project_service"]
    ts = services["task_service"]
    rs = services["resource_service"]

    project = ps.create_project("Res Test", "")
    pid = project.id

    # Create tasks with overlapping periods
    t1 = ts.create_task(pid, "Task 1", start_date=date(2023, 11, 6), duration_days=3)
    t2 = ts.create_task(pid, "Task 2", start_date=date(2023, 11, 7), duration_days=3)

    # Create resource
    r = rs.create_resource("Dev 1", "Developer", hourly_rate=100.0)

    # Assign 50% to t1
    a1 = ts.assign_resource(t1.id, r.id, allocation_percent=50.0)
    assert a1.allocation_percent == 50.0

    # Assign another 40% on overlapping task -> should be OK (total 90%)
    a2 = ts.assign_resource(t2.id, r.id, allocation_percent=40.0)
    assert a2.allocation_percent == 40.0

    # A third overlapping task pushes the resource over 100% across distinct
    # tasks. Warn-only policy: allow the assignment but record an
    # over-allocation warning. (Re-assigning the same resource to the same task
    # is now rejected as ASSIGNMENT_DUPLICATE, so overallocation is exercised
    # via a separate overlapping task.)
    t3 = ts.create_task(pid, "Task 3", start_date=date(2023, 11, 7), duration_days=3)
    ts.assign_resource(t3.id, r.id, allocation_percent=20.0)
    warning_text = ts.consume_last_overallocation_warning()
    assert warning_text is not None
    assert "over-allocated on" in warning_text

    # Check tasks for resource in project
    tasks_for_res = ts.query_tasks(project_id=pid, resource_id=r.id)
    assert len(tasks_for_res) == 3


def test_auto_provisioned_project_resource_rolls_back_with_assignment_failure(
    services, monkeypatch
):
    projects = services["project_service"]
    tasks = services["task_service"]
    resources = services["resource_service"]
    project = projects.create_project("Assignment rollback", "")
    task = tasks.create_task(project.id, "Work")
    resource = resources.create_resource("Rollback resource", "Developer")

    def fail_assignment(**_kwargs):
        raise RuntimeError("assignment rejected")

    monkeypatch.setattr(tasks._assignment_handler, "_assign_project_resource_in_uow", fail_assignment)
    with pytest.raises(RuntimeError, match="assignment rejected"):
        tasks.assign_resource(task.id, resource.id)

    assert tasks._project_resource_repo.get_for_project(project.id, resource.id) is None
    assert tasks._assignment_repo.list_by_task(task.id) == []


def test_auto_provisioned_envelope_and_assignment_roll_back_after_staging(
    services, monkeypatch
):
    projects = services["project_service"]
    tasks = services["task_service"]
    resources = services["resource_service"]
    project = projects.create_project("Assignment staged rollback", "")
    task = tasks.create_task(project.id, "Work")
    resource = resources.create_resource("Staged rollback resource", "Developer")

    def fail_activity(*_args, **_kwargs):
        raise RuntimeError("activity staging rejected")

    monkeypatch.setattr(assignment_commands, "record_assignment_action", fail_activity)
    with pytest.raises(RuntimeError, match="activity staging rejected"):
        tasks.assign_resource(task.id, resource.id)

    assert tasks._project_resource_repo.get_for_project(project.id, resource.id) is None
    assert tasks._assignment_repo.list_by_task(task.id) == []

