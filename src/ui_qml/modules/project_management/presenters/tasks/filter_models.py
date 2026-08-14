from __future__ import annotations

from dataclasses import dataclass

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskSelectorOptionViewModel,
)


@dataclass(frozen=True)
class TaskFilterOptions:
    project_options: tuple[TaskSelectorOptionViewModel, ...]
    status_options: tuple[TaskSelectorOptionViewModel, ...]
    bulk_status_options: tuple[TaskSelectorOptionViewModel, ...]
    priority_options: tuple[TaskSelectorOptionViewModel, ...]
    schedule_options: tuple[TaskSelectorOptionViewModel, ...]


@dataclass(frozen=True)
class NormalizedTaskFilters:
    search_text: str
    status_filter: str
    priority_filter: str
    schedule_filter: str


__all__ = ["NormalizedTaskFilters", "TaskFilterOptions"]
