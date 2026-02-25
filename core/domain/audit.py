from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.domain.identifiers import generate_id


@dataclass
class AuditLogEntry:
    id: str
    occurred_at: datetime
    actor_user_id: str | None
    actor_username: str | None
    action: str
    entity_type: str
    entity_id: str
    project_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(
        action: str,
        entity_type: str,
        entity_id: str,
        *,
        actor_user_id: str | None = None,
        actor_username: str | None = None,
        project_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> "AuditLogEntry":
        return AuditLogEntry(
            id=generate_id(),
            occurred_at=datetime.now(timezone.utc),
            actor_user_id=actor_user_id,
            actor_username=actor_username,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=project_id,
            details=details or {},
        )


__all__ = ["AuditLogEntry"]

