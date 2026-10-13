from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from src.core.modules.project_management.application.tasks.commands.schedule_sync import (
    TaskScheduleSynchronizer,
)


class _TaskRepo:
    def __init__(self) -> None:
        self.reads = 0

    def list_by_project(self, project_id: str):
        assert project_id == "project-1"
        self.reads += 1
        finish = date(2026, 10, 12 if self.reads == 1 else 13)
        return [
            SimpleNamespace(
                id="changed", start_date=date(2026, 10, 10), end_date=finish
            ),
            SimpleNamespace(
                id="excluded", start_date=date(2026, 10, 10), end_date=finish
            ),
        ]


def test_schedule_diff_delegates_commit_policy_and_excludes_primary_task() -> None:
    calls: list[tuple[str, bool]] = []
    scheduler = SimpleNamespace(
        recalculate_project_schedule=lambda project_id, *, commit: calls.append(
            (project_id, commit)
        )
    )
    tasks = _TaskRepo()
    synchronizer = TaskScheduleSynchronizer(
        scheduling_engine=scheduler, task_repo=tasks
    )

    changed = synchronizer.sync_project_schedule(
        "project-1", commit=False, exclude_task_ids=frozenset({"excluded"})
    )

    assert changed == ["changed"]
    assert calls == [("project-1", False)]
    assert tasks.reads == 2
