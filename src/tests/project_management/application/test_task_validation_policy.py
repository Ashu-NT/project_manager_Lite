from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from src.core.modules.project_management.application.tasks.commands import validation
from src.core.modules.project_management.application.tasks.commands.validation import (
    TaskValidationPolicy,
)


class _Tasks:
    def __init__(self) -> None:
        self.batch_calls: list[list[str]] = []

    def get(self, task_id: str):
        if task_id != "new-task":
            raise AssertionError("conflict names must not use per-task get()")
        return SimpleNamespace(
            id=task_id,
            name="New task",
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 2),
        )

    def list_by_ids(self, task_ids: list[str]):
        self.batch_calls.append(task_ids)
        return [SimpleNamespace(id=task_id, name=task_id) for task_id in task_ids]


def test_capacity_conflict_names_use_one_batch(monkeypatch) -> None:
    tasks = _Tasks()
    monkeypatch.setattr(
        validation,
        "evaluate_task_assignment_capacity",
        lambda **_kwargs: SimpleNamespace(
            capacity_status=validation.CAPACITY_OVER_CAPACITY,
            days=[
                SimpleNamespace(
                    status=validation.CAPACITY_OVER_CAPACITY,
                    contributing_task_ids={"task-b", "task-a"},
                )
            ],
            conflict_dates=[date(2026, 10, 1)],
            peak_utilization_percent=150,
        ),
    )
    policy = TaskValidationPolicy(
        task_repo=tasks,
        assignment_repo=SimpleNamespace(),
        resource_repo=SimpleNamespace(),
        project_repo=None,
        availability_service=SimpleNamespace(),
    )

    warning = policy.check_resource_overallocation(
        "project-1", "resource-1", "new-task", 100, overallocation_policy="warn"
    )

    assert warning is not None
    assert "task-a, task-b, New task" in warning
    assert tasks.batch_calls == [["task-a", "task-b"]]
