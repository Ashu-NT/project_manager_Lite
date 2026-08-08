from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class TaskDesktopDto:
    id: str
    project_id: str
    project_name: str
    name: str
    code: str
    description: str
    status: str
    status_label: str
    start_date: date | None
    end_date: date | None
    duration_days: int | None
    priority: int | None
    percent_complete: float
    actual_start: date | None
    actual_end: date | None
    deadline: date | None
    version: int
    parent_task_id: str | None = None
    wbs_code: str = ""
    sort_order: int = 0
    is_summary: bool = False
    hierarchy_depth: int = 0
    child_count: int = 0
    ancestor_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskListResultDto:
    tasks: tuple[TaskDesktopDto, ...] = ()
    skipped_project_ids: tuple[str, ...] = ()

    @property
    def is_partial(self) -> bool:
        return bool(self.skipped_project_ids)


__all__ = ["TaskDesktopDto", "TaskListResultDto"]
