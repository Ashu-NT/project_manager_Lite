from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class DetailActivityDesktopDto:
    id: str
    occurred_at: str
    actor_id: str | None
    action: str
    entity_type: str
    summary: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DetailActivityPageDesktopDto:
    items: tuple[DetailActivityDesktopDto, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = "occurredAt"
    sort_direction: str = "desc"


__all__ = ["DetailActivityDesktopDto", "DetailActivityPageDesktopDto"]
