"""Transport-neutral application response DTOs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskCollaborationReactionSummaryDto:
    emoji: str
    count: int
    reactor_user_ids: tuple[str, ...]
    reacted_by_current_user: bool = False


@dataclass(frozen=True)
class CollaborationContextOptionsDto:
    projects: tuple[tuple[str, str], ...]
    people: tuple[str, ...]

