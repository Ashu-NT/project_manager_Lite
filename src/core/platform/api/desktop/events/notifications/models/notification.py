from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class NotificationDto:
    id: str
    category: str
    title: str
    body: str
    created_at: datetime
    read_at: datetime | None
    is_read: bool
    metadata: dict[str, Any]


__all__ = ["NotificationDto"]
