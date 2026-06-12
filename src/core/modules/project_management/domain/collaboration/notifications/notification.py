from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CollaborationNotificationItem:
    notification_type: str
    entity_type: str
    entity_id: str
    headline: str
    body_preview: str
    actor_username: str
    created_at: datetime
    project_id: str | None = None
    project_name: str = ""
    attention: bool = False


__all__ = ["CollaborationNotificationItem"]
