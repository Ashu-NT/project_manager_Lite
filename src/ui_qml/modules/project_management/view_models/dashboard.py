from __future__ import annotations

from dataclasses import dataclass


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


__all__ = [
    "ProjectDashboardMetricViewModel",
    "ProjectDashboardOverviewViewModel",
]
