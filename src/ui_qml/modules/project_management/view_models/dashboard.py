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
class ProjectDashboardPanelRowViewModel:
    label: str
    value: str
    supporting_text: str = ""
    tone: str = "default"


@dataclass(frozen=True)
class ProjectDashboardPanelViewModel:
    title: str
    subtitle: str = ""
    hint: str = ""
    empty_state: str = ""
    rows: tuple["ProjectDashboardPanelRowViewModel", ...] = field(default_factory=tuple)
    metrics: tuple["ProjectDashboardMetricViewModel", ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProjectDashboardChartPointViewModel:
    label: str
    value: float
    value_label: str = ""
    supporting_text: str = ""
    target_value: float | None = None
    tone: str = "accent"


@dataclass(frozen=True)
class ProjectDashboardChartViewModel:
    title: str
    subtitle: str = ""
    chart_type: str = "bar"
    empty_state: str = ""
    points: tuple["ProjectDashboardChartPointViewModel", ...] = field(default_factory=tuple)


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
    panels: tuple[ProjectDashboardPanelViewModel, ...] = field(default_factory=tuple)
    charts: tuple[ProjectDashboardChartViewModel, ...] = field(default_factory=tuple)
    sections: tuple[ProjectDashboardSectionViewModel, ...] = field(default_factory=tuple)
    empty_state: str = ""


__all__ = [
    "ProjectDashboardChartPointViewModel",
    "ProjectDashboardChartViewModel",
    "ProjectDashboardMetricViewModel",
    "ProjectDashboardOverviewViewModel",
    "ProjectDashboardPanelRowViewModel",
    "ProjectDashboardPanelViewModel",
    "ProjectDashboardSectionItemViewModel",
    "ProjectDashboardSectionViewModel",
    "ProjectDashboardSelectorOptionViewModel",
    "ProjectDashboardWorkspaceViewModel",
]
