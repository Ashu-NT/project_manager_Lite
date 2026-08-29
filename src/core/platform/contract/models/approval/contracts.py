from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApprovalPostCommitEvent:
    signal_name: str
    payload: object


@dataclass(frozen=True)
class ApprovalHandlerResult:
    post_commit_events: tuple[ApprovalPostCommitEvent, ...] = ()


__all__ = [
    "ApprovalHandlerResult",
    "ApprovalPostCommitEvent",
]
