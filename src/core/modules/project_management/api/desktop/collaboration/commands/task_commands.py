"""Collaboration command objects — request payloads for post/update actions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskCollaborationPostCommand:
    task_id: str
    body: str
    attachments: tuple[str, ...] = ()
    linked_document_ids: tuple[str, ...] = ()
    parent_comment_id: str | None = None


@dataclass(frozen=True)
class TaskCollaborationEditCommand:
    comment_id: str
    body: str


@dataclass(frozen=True)
class TaskCollaborationDeleteCommand:
    comment_id: str


@dataclass(frozen=True)
class TaskCollaborationReactionCommand:
    comment_id: str
    emoji: str


__all__ = [
    "TaskCollaborationDeleteCommand",
    "TaskCollaborationEditCommand",
    "TaskCollaborationPostCommand",
    "TaskCollaborationReactionCommand",
]
