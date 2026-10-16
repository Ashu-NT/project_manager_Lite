from __future__ import annotations

from src.core.modules.project_management.api.desktop.resources.models.context import (
    ResourceActivityDesktopDto,
)
from src.core.modules.project_management.contracts.reads.resources.models import (
    ResourceActivityFact,
)


def serialize_resource_activity(fact: ResourceActivityFact) -> ResourceActivityDesktopDto:
    return ResourceActivityDesktopDto(
        id=fact.activity_id,
        resource_id=fact.resource_id,
        occurred_at=fact.occurred_at,
        event_type=fact.event_type,
        category=fact.category,
        actor_id=fact.actor_id,
        actor_kind=fact.actor_kind,
        actor_display=fact.actor_display,
        summary=fact.summary,
        source_type=fact.source_type,
        source_id=fact.source_id,
        project_id=fact.project_id,
        task_id=fact.task_id,
        can_open_source=fact.can_open_source,
    )


__all__ = [
    "serialize_resource_activity",
]
