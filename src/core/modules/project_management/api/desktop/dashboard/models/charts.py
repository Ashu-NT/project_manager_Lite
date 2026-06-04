from __future__ import annotations
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProjectDashboardChartPointDescriptor:
    label: str
    value: float
    value_label: str = ""
    supporting_text: str = ""
    target_value: float | None = None
    tone: str = "accent"


@dataclass(frozen=True)
class ProjectDashboardChartDescriptor:
    title: str
    subtitle: str = ""
    chart_type: str = "bar"
    empty_state: str = ""
    points: tuple[ProjectDashboardChartPointDescriptor, ...] = field(default_factory=tuple)


__all__ = ["ProjectDashboardChartDescriptor", "ProjectDashboardChartPointDescriptor"]
