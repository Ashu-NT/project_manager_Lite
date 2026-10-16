"""Neutral task-discussion responses, independent of desktop presentation."""

from dataclasses import dataclass
from datetime import datetime

from src.core.modules.project_management.application.collaboration.dto.responses.collaboration import (
    TaskCollaborationReactionSummaryDto,
)


@dataclass(frozen=True)
class TaskCommentActionContext:
    principal_user_id: str
    can_read: bool
    can_manage: bool


@dataclass(frozen=True)
class TaskCommentResponseDto:
    id: str
    task_id: str
    author_user_id: str | None
    author_username: str | None
    body: str
    mentions: tuple[str, ...]
    attachments: tuple[str, ...]
    created_at: datetime
    parent_comment_id: str | None
    updated_at: datetime | None
    deleted_at: datetime | None
    deletion_reason: str | None
    reactions: tuple[TaskCollaborationReactionSummaryDto, ...]
    version: int
    parent_author_username: str = ""
    reply_count: int = 0
