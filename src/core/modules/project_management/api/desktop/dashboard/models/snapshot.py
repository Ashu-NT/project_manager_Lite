from __future__ import annotations
from dataclasses import dataclass, field
from src.core.modules.project_management.api.desktop.dashboard.models.overview import ProjectDashboardOverviewDescriptor
from src.core.modules.project_management.api.desktop.dashboard.models.health_cards import ProjectDashboardHealthCardDescriptor
from src.core.modules.project_management.api.desktop.dashboard.models.tables import (
    ProjectDashboardOperationalTabDescriptor,
    ProjectDashboardOperationalTableDescriptor,
)
from src.core.modules.project_management.api.desktop.dashboard.models.charts import ProjectDashboardChartDescriptor
from src.core.modules.project_management.api.desktop.dashboard.models.panels import ProjectDashboardPanelDescriptor
from src.core.modules.project_management.api.desktop.dashboard.models.sections import ProjectDashboardSectionDescriptor
from src.core.modules.project_management.api.desktop.dashboard.models.activity_feed import ProjectDashboardActivityFeedDescriptor


@dataclass(frozen=True)
class ProjectDashboardSelectorOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class ProjectDashboardSnapshotDescriptor:
    overview: ProjectDashboardOverviewDescriptor
    project_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...] = field(default_factory=tuple)
    selected_project_id: str = ""
    baseline_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...] = field(default_factory=tuple)
    selected_baseline_id: str = ""
    period_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...] = field(default_factory=tuple)
    selected_period_key: str = ""
    view_options: tuple[ProjectDashboardSelectorOptionDescriptor, ...] = field(default_factory=tuple)
    selected_view_key: str = ""
    health_cards: tuple[ProjectDashboardHealthCardDescriptor, ...] = field(default_factory=tuple)
    operational_tabs: tuple[ProjectDashboardOperationalTabDescriptor, ...] = field(default_factory=tuple)
    operational_tables: tuple[ProjectDashboardOperationalTableDescriptor, ...] = field(default_factory=tuple)
    activity_feed: ProjectDashboardActivityFeedDescriptor | None = None
    panels: tuple[ProjectDashboardPanelDescriptor, ...] = field(default_factory=tuple)
    charts: tuple[ProjectDashboardChartDescriptor, ...] = field(default_factory=tuple)
    sections: tuple[ProjectDashboardSectionDescriptor, ...] = field(default_factory=tuple)
    empty_state: str = ""


__all__ = ["ProjectDashboardSelectorOptionDescriptor", "ProjectDashboardSnapshotDescriptor"]
