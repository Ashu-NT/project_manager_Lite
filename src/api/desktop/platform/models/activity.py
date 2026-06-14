from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ActivityEntryDto:
    id: str
    action: str
    entity_type: str
    entity_id: str
    actor_id: str | None
    module: str
    timestamp: datetime
    type: str
    human_message: str
    details: dict[str, Any] = field(default_factory=dict)
    icon: str | None = None
    color: str | None = None
    visibility: str = "workspace"
    occurred_at: datetime | None = None  # alias for timestamp, for UI backward compat

    def __post_init__(self) -> None:
        object.__setattr__(self, "occurred_at", self.timestamp)
