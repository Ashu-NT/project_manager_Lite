from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ProjectDashboardActivityItemDescriptor:
    id: str
    title: str
    status_label: str = ""
    occurred_at: datetime | None = None
    actor_display: str = ""
    subject_display: str = ""
    route_id: str = ""
    state: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProjectDashboardActivityFeedDescriptor:
    title: str
    subtitle: str = ""
    empty_state: str = ""
    items: tuple[ProjectDashboardActivityItemDescriptor, ...] = field(default_factory=tuple)


__all__ = ["ProjectDashboardActivityFeedDescriptor", "ProjectDashboardActivityItemDescriptor"]
