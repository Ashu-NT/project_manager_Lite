from __future__ import annotations
from dataclasses import dataclass, field
from src.core.modules.project_management.api.desktop.dashboard.models.overview import ProjectDashboardMetricDescriptor


@dataclass(frozen=True)
class ProjectDashboardPanelRowDescriptor:
    label: str
    value: str
    supporting_text: str = ""
    tone: str = "default"


@dataclass(frozen=True)
class ProjectDashboardPanelDescriptor:
    title: str
    subtitle: str = ""
    hint: str = ""
    empty_state: str = ""
    rows: tuple[ProjectDashboardPanelRowDescriptor, ...] = field(default_factory=tuple)
    metrics: tuple[ProjectDashboardMetricDescriptor, ...] = field(default_factory=tuple)


__all__ = ["ProjectDashboardPanelDescriptor", "ProjectDashboardPanelRowDescriptor"]
