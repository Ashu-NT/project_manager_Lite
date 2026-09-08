from __future__ import annotations

from dataclasses import dataclass

from src.core.shared.events.domain_event import DomainEvent


@dataclass(frozen=True)
class ApprovalHandlerResult:
    domain_events: tuple[DomainEvent, ...] = ()


__all__ = [
    "ApprovalHandlerResult",
]
