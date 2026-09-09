
from __future__ import annotations

from typing import Protocol

from src.core.shared.events.domain_event import DomainEvent
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.persistence.unit_of_work import UnitOfWork


class TransactionalEventDispatcher(Protocol):
    def dispatch(self, event: DomainEvent, uow: UnitOfWork) -> None: ...


class PostCommitEventPublisher(Protocol):
    def publish(self, event: DomainEvent, context: DomainEventContext) -> None: ...


__all__ = ["TransactionalEventDispatcher", "PostCommitEventPublisher"]
