"""Dependency writes roll back when schedule synchronization fails."""

from datetime import date

import pytest

from src.core.modules.project_management.domain.enums import DependencyType


def _two_tasks(services):
    project = services["project_service"].create_project("Dependency Rollback", "")
    tasks = services["task_service"]
    first = tasks.create_task(project.id, "First", start_date=date(2026, 9, 7), duration_days=2)
    second = tasks.create_task(project.id, "Second", start_date=date(2026, 9, 10), duration_days=2)
    return tasks, project, first, second


def _fail_schedule(*args, **kwargs):
    raise RuntimeError("schedule synchronization failed")


def test_add_rolls_back_when_schedule_sync_fails(services, monkeypatch):
    tasks, project, first, second = _two_tasks(services)
    monkeypatch.setattr(
        tasks._dependency_command_handler._schedule_synchronizer,
        "sync_project_schedule",
        _fail_schedule,
    )

    with pytest.raises(RuntimeError, match="schedule synchronization failed"):
        tasks.add_dependency(first.id, second.id, DependencyType.FINISH_TO_START)

    assert tasks.list_dependencies_for_project(project.id) == []


def test_update_rolls_back_when_schedule_sync_fails(services, monkeypatch):
    tasks, _, first, second = _two_tasks(services)
    dependency = tasks.add_dependency(first.id, second.id, DependencyType.FINISH_TO_START)
    monkeypatch.setattr(
        tasks._dependency_command_handler._schedule_synchronizer,
        "sync_project_schedule",
        _fail_schedule,
    )

    with pytest.raises(RuntimeError, match="schedule synchronization failed"):
        tasks.update_dependency(dependency.id, lag_days=2, expected_version=dependency.version)

    unchanged = tasks.get_dependency(dependency.id)
    assert unchanged.lag_days == 0
    assert unchanged.version == dependency.version
