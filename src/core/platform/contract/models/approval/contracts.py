from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.core.shared.events.domain_event import DomainEvent


class ApprovalDecisionInput(Protocol):
    @property
    def request_id(self) -> str: ...

    @property
    def note(self) -> str | None: ...


@dataclass(frozen=True)
class ApprovalHandlerResult:
    domain_events: tuple[DomainEvent, ...] = ()


__all__ = [
    "ApprovalDecisionInput",
    "ApprovalHandlerResult",
]
