from datetime import date

import pytest

from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.infrastructure.persistence.repositories.tasks.task import (
    SqlAlchemyTaskRepository,
)


def test_task_progress_and_status_transitions(services):

    project = services['project_create'].create_project("Progress Test", "")
    pid = project.id

    t = services['task_lifecycle_commands'].create_task(pid, "Task P", start_date=date(2023, 11, 6), duration_days=2)

    assert t.status == TaskStatus.TODO

    t = services['task_progress_commands'].update_progress(t.id, percent_complete=10.0, actual_start=date(2023, 11, 6))
    assert t.status == TaskStatus.IN_PROGRESS
    assert t.actual_start == date(2023, 11, 6)

    t = services['task_progress_commands'].update_progress(t.id, percent_complete=100.0, actual_end=date(2023, 11, 7))
    assert t.status == TaskStatus.DONE
    assert t.actual_end == date(2023, 11, 7)


def test_task_progress_accepts_explicit_status_updates(services):

    project = services['project_create'].create_project("Progress Status Override", "")
    pid = project.id
    t = services['task_lifecycle_commands'].create_task(pid, "Task S", start_date=date(2023, 11, 6), duration_days=2)

    t = services['task_progress_commands'].update_progress(t.id, status=TaskStatus.BLOCKED)
    assert t.status == TaskStatus.BLOCKED

    t = services['task_progress_commands'].update_progress(t.id, percent_complete=100.0, status=TaskStatus.BLOCKED)
    assert t.percent_complete == 100.0
    assert t.status == TaskStatus.BLOCKED


def test_set_status_updates_percent_complete_defaults(services):

    project = services['project_create'].create_project("Status Defaults", "")
    pid = project.id
    task = services['task_lifecycle_commands'].create_task(pid, "Task Defaults", start_date=date(2023, 11, 6), duration_days=2)

    services['task_progress_commands'].set_status(task.id, TaskStatus.DONE)
    task = services['task_detail_query'].get_task(task.id)
    assert task.percent_complete == 100.0

    services['task_progress_commands'].set_status(task.id, TaskStatus.TODO)
    task = services['task_detail_query'].get_task(task.id)
    assert task.percent_complete == 0.0

    services['task_progress_commands'].set_status(task.id, TaskStatus.DONE)
    services['task_progress_commands'].set_status(task.id, TaskStatus.IN_PROGRESS)
    task = services['task_detail_query'].get_task(task.id)
    assert 0.0 < float(task.percent_complete or 0.0) < 100.0


def test_bulk_status_failure_rolls_back_all_tasks(services, monkeypatch):
    project = services['project_create'].create_project("Bulk status rollback")
    first = services['task_lifecycle_commands'].create_task(project.id, "First")
    second = services['task_lifecycle_commands'].create_task(project.id, "Second")
    original_update = SqlAlchemyTaskRepository.update
    calls = 0

    def fail_on_second_update(self, task):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated status failure")
        return original_update(self, task)

    monkeypatch.setattr(SqlAlchemyTaskRepository, "update", fail_on_second_update)
    with pytest.raises(RuntimeError, match="simulated status failure"):
        services['task_progress_commands'].set_tasks_status((first.id, second.id), TaskStatus.DONE)

    services["session"].expire_all()
    assert services['task_detail_query'].get_task(first.id).status == TaskStatus.TODO
    assert services['task_detail_query'].get_task(second.id).status == TaskStatus.TODO

