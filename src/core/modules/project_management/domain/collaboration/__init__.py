"""Collaboration domain — entities, value objects, and mention utilities."""

from src.core.modules.project_management.domain.collaboration.comments.comment import (
    TaskComment,
    normalize_task_comment_body,
)
from src.core.modules.project_management.domain.collaboration.mentions.mention import (
    CollaborationMentionCandidate,
    MENTION_RE,
    candidate_handles,
    extract_mention_tokens,
    resolve_mentions,
)
from src.core.modules.project_management.domain.collaboration.models.workspace import (
    CollaborationContextOptions,
    CollaborationInboxItem,
    CollaborationInboxPage,
)
from src.core.modules.project_management.domain.collaboration.presence.presence import (
    TaskPresence,
    TaskPresenceStatusItem,
)

__all__ = [
    "CollaborationContextOptions",
    "CollaborationInboxItem",
    "CollaborationInboxPage",
    "CollaborationMentionCandidate",
    "MENTION_RE",
    "TaskComment",
    "TaskPresence",
    "TaskPresenceStatusItem",
    "candidate_handles",
    "extract_mention_tokens",
    "normalize_task_comment_body",
    "resolve_mentions",
]
