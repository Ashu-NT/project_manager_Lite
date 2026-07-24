from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class PlatformEvent:
    id: str
    operation: str
    actor_user_id: str | None
    tenant_id: str
    resource_type: str
    resource_id: str
    outcome: str
    severity: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        operation: str,
        actor_user_id: str | None,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        outcome: str = "success",
        severity: str = "low",
        metadata: dict[str, Any] | None = None,
    ) -> PlatformEvent:
        return cls(
            id=str(uuid.uuid4()),
            operation=operation,
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            severity=severity,
            created_at=datetime.now(tz=timezone.utc),
            metadata=metadata or {},
        )


__all__ = ["PlatformEvent"]
