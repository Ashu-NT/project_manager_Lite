from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from src.core.modules.project_management.domain.identifiers import generate_id


@dataclass
class TaskPresence:
    id: str
    task_id: str
    user_id: str | None
    username: str
    display_name: str | None = None
    activity: str = "reviewing"
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def create(*, task_id: str, user_id: str | None, username: str, display_name: str | None = None, activity: str = "reviewing") -> "TaskPresence":
        now = datetime.now(timezone.utc)
        return TaskPresence(
            id=generate_id(), task_id=task_id, user_id=user_id,
            username=(username or "").strip().lower(),
            display_name=(display_name or "").strip() or None,
            activity=(activity or "reviewing").strip().lower(),
            started_at=now, last_seen_at=now,
        )


@dataclass(frozen=True)
class TaskPresenceStatusItem:
    task_id: str
    task_name: str
    project_id: str
    project_name: str
    username: str
    display_name: str | None = None
    activity: str = "reviewing"
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_self: bool = False


__all__ = ["TaskPresence", "TaskPresenceStatusItem"]
