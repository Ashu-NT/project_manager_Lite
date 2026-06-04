"""Collaboration command objects — request payloads for post/update actions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskCollaborationPostCommand:
    task_id: str
    body: str
    attachments: tuple[str, ...] = ()
    linked_document_ids: tuple[str, ...] = ()


__all__ = ["TaskCollaborationPostCommand"]
