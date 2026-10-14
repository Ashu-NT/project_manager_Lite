from __future__ import annotations

from typing import Protocol, TypeVar

from src.core.shared.events.domain_event import DomainEvent
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.subscription import Subscription
from src.core.shared.persistence.unit_of_work import UnitOfWork

E_contra = TypeVar("E_contra", bound=DomainEvent, contravariant=True)


class TransactionalEventHandler(Protocol[E_contra]):
    def __call__(self, event: E_contra, uow: UnitOfWork) -> None: ...


class PostCommitEventHandler(Protocol[E_contra]):
    def __call__(self, event: E_contra, context: DomainEventContext) -> None: ...


class TransactionalEventSubscriber(Protocol):
    def subscribe(
        self, event_type: type[E_contra], handler: TransactionalEventHandler[E_contra]
    ) -> Subscription: ...


class PostCommitEventSubscriber(Protocol):
    def subscribe(
        self, event_type: type[E_contra], handler: PostCommitEventHandler[E_contra]
    ) -> Subscription: ...


__all__ = [
    "PostCommitEventHandler",
    "PostCommitEventSubscriber",
    "TransactionalEventHandler",
    "TransactionalEventSubscriber",
]
