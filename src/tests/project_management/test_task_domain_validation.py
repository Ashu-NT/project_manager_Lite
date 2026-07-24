from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment, TaskDependency
from src.core.platform.common.exceptions import ValidationError


def test_task_dto_normalizes_and_validates_fields():
    task = Task.create(
        project_id="  project-1  ",
        name="  Cable Pull  ",
        description="  Primary cable run  ",
        code="  tsk-manual-1  ",
        start_date=date(2026, 7, 6),
        duration_days="4",
        percent_complete="25",
        deadline=date(2026, 7, 10),
    )

    assert task.project_id == "project-1"
    assert task.name == "Cable Pull"
    assert task.description == "Primary cable run"
    assert task.code == "tsk-manual-1"
    assert task.duration_days == 4
    assert task.percent_complete == pytest.approx(25.0)


def test_task_dto_rejects_invalid_name_and_dates():
    with pytest.raises(ValidationError) as exc_empty:
        Task.create(project_id="project-1", name="  ")
    assert exc_empty.value.code == "TASK_NAME_EMPTY"

    with pytest.raises(ValidationError) as exc_short:
        Task.create(project_id="project-1", name="AB")
    assert exc_short.value.code == "TASK_NAME_TOO_SHORT"

    with pytest.raises(ValidationError) as exc_chars:
        Task.create(project_id="project-1", name="Bad/Name")
    assert exc_chars.value.code == "TASK_NAME_INVALID_CHARS"

    with pytest.raises(ValidationError) as exc_deadline:
        Task.create(
            project_id="project-1",
            name="Deadline Check",
            start_date=date(2026, 7, 10),
            deadline=date(2026, 7, 9),
        )
    assert exc_deadline.value.code == "TASK_DEADLINE_INVALID"


def test_task_dto_rejects_invalid_progress_and_actual_dates():
    with pytest.raises(ValidationError) as exc_percent:
        Task.create(project_id="project-1", name="Progress Check", percent_complete=101)
    assert exc_percent.value.code == "TASK_PERCENT_COMPLETE_INVALID"

    with pytest.raises(ValidationError) as exc_actual:
        Task.create(
            project_id="project-1",
            name="Actual Date Check",
            actual_start=date(2026, 7, 10),
            actual_end=date(2026, 7, 9),
        )
    assert exc_actual.value.code == "TASK_ACTUAL_DATE_RANGE_INVALID"


def test_task_assignment_dto_validates_allocation_and_hours():
    assignment = TaskAssignment.create(
        task_id="  task-1  ",
        resource_id="  resource-1  ",
        allocation_percent="60",
        hours_logged="4.5",
    )
    assignment.project_resource_id = "  project-resource-1  "

    assert assignment.task_id == "task-1"
    assert assignment.resource_id == "resource-1"
    assert assignment.allocation_percent == pytest.approx(60.0)
    assert assignment.hours_logged == pytest.approx(4.5)
    assert assignment.project_resource_id == "project-resource-1"

    with pytest.raises(ValidationError) as exc_alloc:
        TaskAssignment.create("task-1", "resource-1", allocation_percent=0)
    assert exc_alloc.value.code == "ASSIGNMENT_ALLOCATION_INVALID"

    with pytest.raises(ValidationError) as exc_hours:
        TaskAssignment.create("task-1", "resource-1", hours_logged=-1)
    assert exc_hours.value.code == "ASSIGNMENT_HOURS_INVALID"


def test_task_dependency_dto_rejects_self_dependency():
    with pytest.raises(ValidationError) as exc:
        TaskDependency.create("task-1", "task-1")

    assert exc.value.code == "DEPENDENCY_SELF"


def test_task_service_update_validates_final_state_and_persists_code(services):
    project_service = services["project_service"]
    task_service = services["task_service"]

    project = project_service.create_project("Task DTO Service", "")
    task = task_service.create_task(
        project.id,
        "Task Validation",
        start_date=date(2026, 7, 6),
        duration_days=2,
    )

    updated = task_service.update_task(
        task.id,
        expected_version=task.version,
        start_date=date(2026, 7, 13),
        duration_days=4,
        code="TSK-REN-1",
    )

    assert updated.start_date == date(2026, 7, 13)
    assert updated.end_date == date(2026, 7, 16)
    assert updated.code == "TSK-REN-1"

    reloaded = task_service.get_task(task.id)
    assert reloaded is not None
    assert reloaded.code == "TSK-REN-1"


def test_task_service_progress_update_uses_final_state_validation(services):
    project_service = services["project_service"]
    task_service = services["task_service"]

    project = project_service.create_project("Task Progress DTO", "")
    task = task_service.create_task(project.id, "Progress Task", duration_days=1)

    with pytest.raises(ValidationError) as exc:
        task_service.update_progress(
            task.id,
            actual_start=date(2026, 7, 10),
            actual_end=date(2026, 7, 9),
        )

    assert exc.value.code == "TASK_ACTUAL_DATE_RANGE_INVALID"
