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
    is_milestone: bool = False


@dataclass(frozen=True)
class TaskWorkspacePageDesktopDto:
    items: tuple[TaskDesktopDto, ...] = ()
    filtered_total: int = 0
    total: int = 0
    in_progress: int = 0
    blocked: int = 0
    done: int = 0
    overdue: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = "wbsCode"
    sort_direction: str = "asc"


__all__ = ["TaskDesktopDto", "TaskWorkspacePageDesktopDto"]
