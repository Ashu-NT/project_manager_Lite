from __future__ import annotations

from dataclasses import dataclass

from src.core.shared.events.domain_event import DomainEvent


@dataclass(frozen=True)
class ApprovalPostCommitEvent:
    signal_name: str
    payload: object


@dataclass(frozen=True)
class ApprovalHandlerResult:
    post_commit_events: tuple[ApprovalPostCommitEvent, ...] = ()
    domain_events: tuple[DomainEvent, ...] = ()


__all__ = [
    "ApprovalHandlerResult",
    "ApprovalPostCommitEvent",
]
