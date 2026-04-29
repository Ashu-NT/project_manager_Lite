from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProjectDashboardMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class ProjectDashboardOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[ProjectDashboardMetricViewModel, ...]


@dataclass(frozen=True)
class ProjectDashboardSelectorOptionViewModel:
    value: str
    label: str


@dataclass(frozen=True)
class ProjectDashboardSectionItemViewModel:
    id: str
    title: str
    status_label: str = ""
    subtitle: str = ""
    supporting_text: str = ""
    meta_text: str = ""
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectDashboardSectionViewModel:
    title: str
    subtitle: str = ""
    empty_state: str = ""
    items: tuple[ProjectDashboardSectionItemViewModel, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProjectDashboardWorkspaceViewModel:
    overview: ProjectDashboardOverviewViewModel
    project_options: tuple[ProjectDashboardSelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_project_id: str = ""
    baseline_options: tuple[ProjectDashboardSelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_baseline_id: str = ""
    sections: tuple[ProjectDashboardSectionViewModel, ...] = field(default_factory=tuple)
    empty_state: str = ""


__all__ = [
    "ProjectDashboardMetricViewModel",
    "ProjectDashboardOverviewViewModel",
    "ProjectDashboardSectionItemViewModel",
    "ProjectDashboardSectionViewModel",
    "ProjectDashboardSelectorOptionViewModel",
    "ProjectDashboardWorkspaceViewModel",
]
