from datetime import date

import pytest

from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.infrastructure.persistence.repositories.tasks.task import (
    SqlAlchemyTaskRepository,
)


def test_task_progress_and_status_transitions(services):
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project("Progress Test", "")
    pid = project.id

    t = ts.create_task(pid, "Task P", start_date=date(2023, 11, 6), duration_days=2)

    assert t.status == TaskStatus.TODO

    t = ts.update_progress(t.id, percent_complete=10.0, actual_start=date(2023, 11, 6))
    assert t.status == TaskStatus.IN_PROGRESS
    assert t.actual_start == date(2023, 11, 6)

    t = ts.update_progress(t.id, percent_complete=100.0, actual_end=date(2023, 11, 7))
    assert t.status == TaskStatus.DONE
    assert t.actual_end == date(2023, 11, 7)


def test_task_progress_accepts_explicit_status_updates(services):
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project("Progress Status Override", "")
    pid = project.id
    t = ts.create_task(pid, "Task S", start_date=date(2023, 11, 6), duration_days=2)

    t = ts.update_progress(t.id, status=TaskStatus.BLOCKED)
    assert t.status == TaskStatus.BLOCKED

    t = ts.update_progress(t.id, percent_complete=100.0, status=TaskStatus.BLOCKED)
    assert t.percent_complete == 100.0
    assert t.status == TaskStatus.BLOCKED


def test_set_status_updates_percent_complete_defaults(services):
    ps = services["project_service"]
    ts = services["task_service"]

    project = ps.create_project("Status Defaults", "")
    pid = project.id
    task = ts.create_task(pid, "Task Defaults", start_date=date(2023, 11, 6), duration_days=2)

    ts.set_status(task.id, TaskStatus.DONE)
    task = ts.get_task(task.id)
    assert task.percent_complete == 100.0

    ts.set_status(task.id, TaskStatus.TODO)
    task = ts.get_task(task.id)
    assert task.percent_complete == 0.0

    ts.set_status(task.id, TaskStatus.DONE)
    ts.set_status(task.id, TaskStatus.IN_PROGRESS)
    task = ts.get_task(task.id)
    assert 0.0 < float(task.percent_complete or 0.0) < 100.0


def test_bulk_status_failure_rolls_back_all_tasks(services, monkeypatch):
    project = services["project_service"].create_project("Bulk status rollback")
    tasks = services["task_service"]
    first = tasks.create_task(project.id, "First")
    second = tasks.create_task(project.id, "Second")
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
        tasks.set_tasks_status((first.id, second.id), TaskStatus.DONE)

    services["session"].expire_all()
    assert tasks.get_task(first.id).status == TaskStatus.TODO
    assert tasks.get_task(second.id).status == TaskStatus.TODO

