from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from dataclasses import field
from uuid import uuid4


class TaskCommentChangeType(str, Enum):
    CREATED = "CREATED"
    EDITED = "EDITED"
    REMOVED = "REMOVED"


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskCommentChanged:
    event_id: str = field(default_factory=lambda: str(uuid4()))

    tenant_id: str
    organization_id: str
    project_id: str
    task_id: str
    comment_id: str
    change_type: TaskCommentChangeType
    occurred_at: datetime


class TaskCommentReactionChangeType(str, Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskCommentReactionChanged:

    tenant_id: str
    organization_id: str
    project_id: str
    task_id: str
    comment_id: str
    change_type: TaskCommentReactionChangeType
    occurred_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class TaskCommentReadStateChanged:
    """A mention read-receipt on a comment changed. Always a "became read" transition (marking
    is one-directional in the current domain), so there is no `change_type` -- unlike
    `TaskCommentChanged`/`TaskCommentReactionChanged`, which each have more than one direction."""

    tenant_id: str
    organization_id: str
    project_id: str
    task_id: str
    comment_id: str
    occurred_at: datetime


__all__ = [
    "TaskCommentChangeType",
    "TaskCommentChanged",
    "TaskCommentReactionChangeType",
    "TaskCommentReactionChanged",
    "TaskCommentReadStateChanged",
]
