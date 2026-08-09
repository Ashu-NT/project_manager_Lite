from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class TaskWorkspaceCondition:
    field: str
    operator: str
    value: str


@dataclass(frozen=True, slots=True)
class TaskWorkspaceCriteria:
    project_id: str | None = None
    search_terms: tuple[str, ...] = ()
    conditions: tuple[TaskWorkspaceCondition, ...] = ()
    status: str = "all"
    priority: str = "all"
    schedule: str = "all"
    as_of: date | None = None


@dataclass(frozen=True, slots=True)
class TaskWorkspaceReadItem:
    id: str
    project_id: str
    project_name: str
    name: str
    code: str
    description: str
    status: str
    start_date: date | None
    end_date: date | None
    duration_days: int | None
    priority: int
    percent_complete: float
    actual_start: date | None
    actual_end: date | None
    deadline: date | None
    version: int
    parent_task_id: str | None
    wbs_code: str
    sort_order: int
    is_summary: bool
    hierarchy_depth: int
    child_count: int


@dataclass(frozen=True, slots=True)
class TaskWorkspaceSummary:
    total: int = 0
    in_progress: int = 0
    blocked: int = 0
    done: int = 0
    overdue: int = 0


@dataclass(frozen=True, slots=True)
class TaskWorkspaceReadPage:
    items: tuple[TaskWorkspaceReadItem, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    summary: TaskWorkspaceSummary = TaskWorkspaceSummary()


__all__ = [
    "TaskWorkspaceCondition",
    "TaskWorkspaceCriteria",
    "TaskWorkspaceReadItem",
    "TaskWorkspaceReadPage",
    "TaskWorkspaceSummary",
]
