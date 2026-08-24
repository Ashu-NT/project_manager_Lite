from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TaskDependencyDesktopDto:
    id: str
    direction: str
    direction_label: str
    linked_task_id: str
    linked_task_name: str
    dependency_type: str
    dependency_type_label: str
    lag_days: int
    relationship_label: str
    version: int = 1
    linked_task_code: str = ""
    linked_task_status: str = ""
    linked_task_start: str = ""
    linked_task_end: str = ""


@dataclass(frozen=True)
class TaskDependencyPageDesktopDto:
    items: tuple[TaskDependencyDesktopDto, ...] = ()
    filtered_total: int = 0
    predecessor_total: int = 0
    successor_total: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = "linkedTask"
    sort_direction: str = "asc"


@dataclass(frozen=True)
class TaskDependencyImpactRowDesktopDto:
    task_id: str
    task_name: str
    before_start_label: str
    before_finish_label: str
    after_start_label: str
    after_finish_label: str
    start_shift_days: int | None
    finish_shift_days: int | None


@dataclass(frozen=True)
class TaskDependencyImpactPreviewDesktopDto:
    """Non-persisting impact preview for a dependency change (create,
    update, or delete) -- Phase K. QML performs zero schedule calculation;
    every date/shift here comes straight from the same canonical CPM
    engine that produces the committed schedule."""

    is_valid: bool
    code: str
    summary: str
    detail: str
    risk_level: str
    affected_task_count: int
    largest_shift_days: int
    rows: tuple[TaskDependencyImpactRowDesktopDto, ...] = field(default_factory=tuple)
    suggestions: tuple[str, ...] = field(default_factory=tuple)


__all__ = [
    "TaskDependencyDesktopDto",
    "TaskDependencyPageDesktopDto",
    "TaskDependencyImpactRowDesktopDto",
    "TaskDependencyImpactPreviewDesktopDto",
]
