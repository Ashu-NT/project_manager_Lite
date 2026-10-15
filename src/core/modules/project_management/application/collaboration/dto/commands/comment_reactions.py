"""Task collaboration use-case commands."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskCollaborationReactionCommand:
    comment_id: str
    emoji: str


__all__ = ["TaskCollaborationReactionCommand"]
