"""Task lifecycle writes remain atomic after the command-handler cutover."""

import pytest

from src.core.modules.project_management.application.tasks.commands import (
    lifecycle as lifecycle_commands,
)


def _fail_activity(*args, **kwargs):
    raise RuntimeError("activity write failed")


def test_create_rolls_back_when_activity_write_fails(services, monkeypatch):
    project = services['project_create'].create_project("Task Lifecycle Rollback", "")
    monkeypatch.setattr(lifecycle_commands, "record_activity", _fail_activity)

    with pytest.raises(RuntimeError, match="activity write failed"):
        services['task_lifecycle_commands'].create_task(project.id, "Uncommitted Task")

    assert services['task_lookup_query'].list_tasks_for_project(project.id) == []


def test_update_rolls_back_when_activity_write_fails(services, monkeypatch):
    project = services['project_create'].create_project("Task Update Rollback", "")
    task = services['task_lifecycle_commands'].create_task(project.id, "Original Task")
    monkeypatch.setattr(lifecycle_commands, "record_activity", _fail_activity)

    with pytest.raises(RuntimeError, match="activity write failed"):
        services['task_lifecycle_commands'].update_task(task.id, name="Uncommitted Rename", expected_version=task.version)

    unchanged = services['task_detail_query'].get_task(task.id)
    assert unchanged.name == "Original Task"
    assert unchanged.version == task.version
