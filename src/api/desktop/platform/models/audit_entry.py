from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class AuditEntryDto:
    id: str
    timestamp: datetime
    operation: str
    entity_type: str
    entity_id: str
    module: str
    actor_id: str | None
    actor_username: str | None
    actor_type: str
    source: str
    severity: str
    compliance_tag: str
    tenant_id: str | None = None
    organization_id: str | None = None
    entity_parent_id: str | None = None
    changed_field: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
