from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class AuditLogEntryDto:
    id: str
    occurred_at: datetime
    actor_user_id: str | None
    actor_username: str | None
    action: str
    entity_type: str
    entity_id: str
    project_id: str | None
    details: dict[str, Any] = field(default_factory=dict)
    project_label: str = "-"
    entity_label: str = "-"
    details_label: str = "-"
