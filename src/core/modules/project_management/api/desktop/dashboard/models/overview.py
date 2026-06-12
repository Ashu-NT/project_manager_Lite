from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectDashboardMetricDescriptor:
    label: str
    value: str
    supporting_text: str


@dataclass(frozen=True)
class ProjectDashboardOverviewDescriptor:
    title: str
    subtitle: str
    metrics: tuple[ProjectDashboardMetricDescriptor, ...]


__all__ = ["ProjectDashboardMetricDescriptor", "ProjectDashboardOverviewDescriptor"]
