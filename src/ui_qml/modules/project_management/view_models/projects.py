from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProjectCatalogMetricViewModel:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class ProjectCatalogOverviewViewModel:
    title: str
    subtitle: str
    metrics: tuple[ProjectCatalogMetricViewModel, ...]


@dataclass(frozen=True)
class ProjectStatusOptionViewModel:
    value: str
    label: str


@dataclass(frozen=True)
class ProjectRecordViewModel:
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
class ProjectDetailFieldViewModel:
    label: str
    value: str
    supporting_text: str = ""


@dataclass(frozen=True)
class ProjectDetailViewModel:
    id: str = ""
    title: str = ""
    status_label: str = ""
    subtitle: str = ""
    description: str = ""
    empty_state: str = ""
    fields: tuple[ProjectDetailFieldViewModel, ...] = field(default_factory=tuple)
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectCatalogWorkspaceViewModel:
    overview: ProjectCatalogOverviewViewModel
    status_options: tuple[ProjectStatusOptionViewModel, ...] = field(default_factory=tuple)
    selected_status_filter: str = "all"
    search_text: str = ""
    projects: tuple[ProjectRecordViewModel, ...] = field(default_factory=tuple)
    selected_project_id: str = ""
    selected_project_detail: ProjectDetailViewModel = field(
        default_factory=ProjectDetailViewModel
    )
    empty_state: str = ""


__all__ = [
    "ProjectCatalogMetricViewModel",
    "ProjectCatalogOverviewViewModel",
    "ProjectCatalogWorkspaceViewModel",
    "ProjectDetailFieldViewModel",
    "ProjectDetailViewModel",
    "ProjectRecordViewModel",
    "ProjectStatusOptionViewModel",
]
