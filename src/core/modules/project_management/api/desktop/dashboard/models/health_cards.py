from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectDashboardHealthCardDescriptor:
    id: str
    title: str
    status_label: str = ""
    metric_value: str = ""
    metric_label: str = ""
    supporting_text: str = ""
    meta_text: str = ""
    tone: str = "default"
    route_id: str = ""


__all__ = ["ProjectDashboardHealthCardDescriptor"]
