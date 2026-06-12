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
class ProjectDashboardHealthCardViewModel:
    id: str
    title: str
    status_label: str = ""
    metric_value: str = ""
    metric_label: str = ""
    supporting_text: str = ""
    meta_text: str = ""
    tone: str = "default"
    route_id: str = ""

@dataclass(frozen=True)
class ProjectDashboardTableColumnViewModel:
    key: str
    label: str
    flex: int = 1
    min_width: int = 120
    sortable: bool = False
    visible: bool = True
    column_type: str = "text"

@dataclass(frozen=True)
class ProjectDashboardTableRowViewModel:
    id: str
    values: dict[str, Any] = field(default_factory=dict)
    route_id: str = ""
    state: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ProjectDashboardOperationalTabViewModel:
    id: str
    label: str
    count: int = 0
    route_id: str = ""

@dataclass(frozen=True)
class ProjectDashboardOperationalTableViewModel:
    id: str
    title: str
    subtitle: str = ""
    empty_state: str = ""
    columns: tuple[ProjectDashboardTableColumnViewModel, ...] = field(
        default_factory=tuple
    )
    rows: tuple[ProjectDashboardTableRowViewModel, ...] = field(default_factory=tuple)

@dataclass(frozen=True)
class ProjectDashboardActivityItemViewModel:
    id: str
    title: str
    status_label: str = ""
    meta_text: str = ""
    route_id: str = ""
    state: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ProjectDashboardActivityFeedViewModel:
    title: str
    subtitle: str = ""
    empty_state: str = ""
    items: tuple[ProjectDashboardActivityItemViewModel, ...] = field(
        default_factory=tuple
    )

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
    period_options: tuple[ProjectDashboardSelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_period_key: str = ""
    view_options: tuple[ProjectDashboardSelectorOptionViewModel, ...] = field(
        default_factory=tuple
    )
    selected_view_key: str = ""
    health_cards: tuple[ProjectDashboardHealthCardViewModel, ...] = field(
        default_factory=tuple
    )
    operational_tabs: tuple[ProjectDashboardOperationalTabViewModel, ...] = field(
        default_factory=tuple
    )
    operational_tables: tuple[ProjectDashboardOperationalTableViewModel, ...] = field(
        default_factory=tuple
    )
    activity_feed: ProjectDashboardActivityFeedViewModel | None = None
    panels: tuple[ProjectDashboardPanelViewModel, ...] = field(default_factory=tuple)
    charts: tuple[ProjectDashboardChartViewModel, ...] = field(default_factory=tuple)
    sections: tuple[ProjectDashboardSectionViewModel, ...] = field(default_factory=tuple)
    empty_state: str = ""

__all__ = [
    "ProjectDashboardChartPointViewModel",
    "ProjectDashboardChartViewModel",
    "ProjectDashboardActivityFeedViewModel",
    "ProjectDashboardActivityItemViewModel",
    "ProjectDashboardHealthCardViewModel",
    "ProjectDashboardMetricViewModel",
    "ProjectDashboardOverviewViewModel",
    "ProjectDashboardOperationalTableViewModel",
    "ProjectDashboardOperationalTabViewModel",
    "ProjectDashboardPanelRowViewModel",
    "ProjectDashboardPanelViewModel",
    "ProjectDashboardSectionItemViewModel",
    "ProjectDashboardSectionViewModel",
    "ProjectDashboardSelectorOptionViewModel",
    "ProjectDashboardTableColumnViewModel",
    "ProjectDashboardTableRowViewModel",
    "ProjectDashboardWorkspaceViewModel",
]
