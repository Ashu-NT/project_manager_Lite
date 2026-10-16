from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ResourceActivityDesktopDto:
    id: str
    resource_id: str
    occurred_at: datetime
    event_type: str
    category: str
    actor_id: str | None
    summary: str
    source_type: str
    source_id: str | None
    project_id: str | None
    task_id: str | None
    can_open_source: bool
    actor_kind: str = "missing"
    actor_display: str = "Deleted user"


@dataclass(frozen=True, slots=True)
class ResourceActivityPageDesktopDto:
    items: tuple[ResourceActivityDesktopDto, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = "occurredAt"
    sort_direction: str = "desc"


__all__ = [
    "ResourceActivityDesktopDto",
    "ResourceActivityPageDesktopDto",
]
