from __future__ import annotations

from types import SimpleNamespace

from src.core.modules.project_management.application.tasks.queries import task_lookup
from src.core.modules.project_management.application.tasks.queries.task_lookup import (
    TaskLookupQueryHandler,
)


class _TaskRepo:
    def __init__(self) -> None:
        self.tasks = {
            "task-a": SimpleNamespace(id="task-a", project_id="project-allowed"),
            "task-b": SimpleNamespace(id="task-b", project_id="project-denied"),
        }
        self.batch_calls: list[list[str]] = []

    def list_by_ids(self, task_ids: list[str]) -> list[SimpleNamespace]:
        self.batch_calls.append(task_ids)
        return [self.tasks[task_id] for task_id in task_ids if task_id in self.tasks]

    def get(self, _task_id: str) -> None:
        raise AssertionError("per-task get() would cause N+1 reads")


class _AssignmentRepo:
    def __init__(self) -> None:
        self.assignments = [
            SimpleNamespace(task_id="task-a", resource_id="resource-1"),
            SimpleNamespace(task_id="task-b", resource_id="resource-1"),
        ]
        self.by_tasks_calls: list[list[str]] = []

    def list_by_resource(self, _resource_id: str) -> list[SimpleNamespace]:
        return self.assignments

    def list_by_tasks(self, task_ids: list[str]) -> list[SimpleNamespace]:
        self.by_tasks_calls.append(task_ids)
        return [item for item in self.assignments if item.task_id in task_ids]


def test_resource_task_lookups_batch_and_filter_by_project(monkeypatch) -> None:
    monkeypatch.setattr(
        task_lookup, "require_permission", lambda *_args, **_kwargs: None
    )
    tasks = _TaskRepo()
    assignments = _AssignmentRepo()
    session = SimpleNamespace(
        has_project_permission=lambda project_id, _permission: (
            project_id == "project-allowed"
        )
    )
    handler = TaskLookupQueryHandler(
        task_repo=tasks,
        assignment_repo=assignments,
        user_session=session,
    )

    assert [task.id for task in handler.list_tasks_for_resource("resource-1")] == [
        "task-a"
    ]
    assert [
        item.task_id for item in handler.list_assignments_for_resource("resource-1")
    ] == ["task-a"]
    assert [
        item.task_id
        for item in handler.list_assignments_for_tasks(["task-a", "task-b", "task-a"])
    ] == ["task-a"]
    assert tasks.batch_calls == [
        ["task-a", "task-b"],
        ["task-a", "task-b"],
        ["task-a", "task-b"],
    ]
    assert assignments.by_tasks_calls == [["task-a"]]
