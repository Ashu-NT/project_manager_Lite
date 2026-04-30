from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TaskCatalogMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class TaskCatalogOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[TaskCatalogMetricViewModel, ...]


@dataclass(frozen=True)
class TaskSelectorOptionViewModel:
    value: str
    label: str


@dataclass(frozen=True)
class TaskRecordViewModel:
    id: str
    title: str
    status_label: str
    subtitle: str
    supporting_text: str
    meta_text: str
    can_primary_action: bool = True
    can_secondary_action: bool = True
    can_tertiary_action: bool = True
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskDetailFieldViewModel:
    label: str
    value: str
    supporting_text: str = ""


@dataclass(frozen=True)
class TaskDetailViewModel:
    id: str = ""
    title: str = ""
    status_label: str = ""
    subtitle: str = ""
    description: str = ""
    empty_state: str = ""
    fields: tuple[TaskDetailFieldViewModel, ...] = field(default_factory=tuple)
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskCatalogWorkspaceViewModel:
    overview: TaskCatalogOverviewViewModel
    project_options: tuple[TaskSelectorOptionViewModel, ...] = field(default_factory=tuple)
    selected_project_id: str = ""
    status_options: tuple[TaskSelectorOptionViewModel, ...] = field(default_factory=tuple)
    selected_status_filter: str = "all"
    search_text: str = ""
    tasks: tuple[TaskRecordViewModel, ...] = field(default_factory=tuple)
    selected_task_id: str = ""
    selected_task_detail: TaskDetailViewModel = field(default_factory=TaskDetailViewModel)
    empty_state: str = ""


__all__ = [
    "TaskCatalogMetricViewModel",
    "TaskCatalogOverviewViewModel",
    "TaskCatalogWorkspaceViewModel",
    "TaskDetailFieldViewModel",
    "TaskDetailViewModel",
    "TaskRecordViewModel",
    "TaskSelectorOptionViewModel",
]
