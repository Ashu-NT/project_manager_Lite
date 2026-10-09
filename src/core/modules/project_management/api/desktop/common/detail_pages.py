from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DetailActivityDesktopDto:
    id: str
    occurred_at: datetime
    actor_id: str | None
    action: str
    entity_type: str
    summary: str
    details: dict[str, object] = field(default_factory=dict)
    actor_kind: str = "missing"
    actor_display: str = "Deleted user"


@dataclass(frozen=True, slots=True)
class DetailActivityPageDesktopDto:
    items: tuple[DetailActivityDesktopDto, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = "occurredAt"
    sort_direction: str = "desc"
    reference_labels: dict[str, dict[str, str]] = field(default_factory=dict)


__all__ = ["DetailActivityDesktopDto", "DetailActivityPageDesktopDto"]
