"""ADR-005 §7 (Transactional Dispatch) and §8 (Post-Commit Publication): the handler shapes
and subscriber contracts.

Each handler shape is a named `Protocol`, never an inline `Callable[...]` repeated at every use
site, so the shape can't drift between a bus's internal registry, registration functions, and
any future adapter (ADR-005 §7). `TransactionalEventHandler` receives the current `UnitOfWork`
(FAIL_FAST -- a handler needing another aggregate touches it through that same `uow`, in the
same transaction); `PostCommitEventHandler` receives a `DomainEventContext` instead
(ISOLATE_AND_CONTINUE -- the transaction is already closed by the time it runs).

`UnitOfWork` is defined in P3 and does not exist yet -- referenced below only as a bare forward
reference under `from __future__ import annotations` (see domain_event_publisher.py for the
same pattern), never imported.

No concrete dispatcher/bus/handler registry here -- P2/P3.
"""

from __future__ import annotations

from typing import Protocol, TypeVar

from src.core.shared.events.domain_event import DomainEvent
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.subscription import Subscription

E = TypeVar("E", bound=DomainEvent)


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
