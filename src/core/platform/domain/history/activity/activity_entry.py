from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.core.platform.common.ids import generate_id


@dataclass
class ActivityEntry:
    id: str
    action: str
    entity_type: str
    entity_id: str
    actor_id: str | None
    actor_role: str | None
    module: str
    workspace_id: str | None
    tenant_id: str | None
    organization_id: str | None
    timestamp: datetime
    type: str  # info | warning | system | user
    human_message: str
    details: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    parent_entity_id: str | None = None
    icon: str | None = None
    color: str | None = None
    visibility: str = "workspace"  # public | workspace | private

    @staticmethod
    def create(
        action: str,
        entity_type: str,
        entity_id: str,
        module: str,
        *,
        actor_id: str | None = None,
        actor_role: str | None = None,
        workspace_id: str | None = None,
        tenant_id: str | None = None,
        organization_id: str | None = None,
        type: str = "info",
        human_message: str = "",
        details: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
        parent_entity_id: str | None = None,
        icon: str | None = None,
        color: str | None = None,
        visibility: str = "workspace",
    ) -> "ActivityEntry":
        return ActivityEntry(
            id=generate_id(),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            actor_role=actor_role,
            module=module,
            workspace_id=workspace_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            timestamp=datetime.now(timezone.utc),
            type=type,
            human_message=human_message or action,
            details=details or {},
            context=context or {},
            parent_entity_id=parent_entity_id,
            icon=icon,
            color=color,
            visibility=visibility,
        )


__all__ = ["ActivityEntry"]
