from __future__ import annotations

from typing import Protocol, TypeVar

from src.core.shared.events.domain_event import DomainEvent
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.subscription import Subscription
from src.core.shared.persistence.unit_of_work import UnitOfWork

E = TypeVar("E", bound=DomainEvent, contravariant=True)


class TransactionalEventHandler(Protocol[E]):
    def __call__(self, event: E, uow: UnitOfWork) -> None: ...


class PostCommitEventHandler(Protocol[E]):
    def __call__(self, event: E, context: DomainEventContext) -> None: ...


class TransactionalEventSubscriber(Protocol):
    def subscribe(
        self, event_type: type[E], handler: TransactionalEventHandler[E]
    ) -> Subscription: ...


class PostCommitEventSubscriber(Protocol):
    def subscribe(
        self, event_type: type[E], handler: PostCommitEventHandler[E]
    ) -> Subscription: ...


__all__ = [
    "TransactionalEventHandler",
    "PostCommitEventHandler",
    "TransactionalEventSubscriber",
    "PostCommitEventSubscriber",
]
