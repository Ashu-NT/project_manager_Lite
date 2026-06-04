"""Collaboration domain — entities, value objects, and mention utilities."""

from src.core.modules.project_management.domain.collaboration.comments.comment import TaskComment
from src.core.modules.project_management.domain.collaboration.mentions.mention import (
    CollaborationMentionCandidate,
    MENTION_RE,
    candidate_handles,
    extract_mention_tokens,
    resolve_mentions,
)
from src.core.modules.project_management.domain.collaboration.models.workspace import (
    CollaborationInboxItem,
    CollaborationWorkspaceSnapshot,
)
from src.core.modules.project_management.domain.collaboration.notifications.notification import (
    CollaborationNotificationItem,
)
from src.core.modules.project_management.domain.collaboration.presence.presence import (
    TaskPresence,
    TaskPresenceStatusItem,
)

__all__ = [
    "CollaborationInboxItem",
    "CollaborationMentionCandidate",
    "CollaborationNotificationItem",
    "CollaborationWorkspaceSnapshot",
    "MENTION_RE",
    "TaskComment",
    "TaskPresence",
    "TaskPresenceStatusItem",
    "candidate_handles",
    "extract_mention_tokens",
    "resolve_mentions",
]
