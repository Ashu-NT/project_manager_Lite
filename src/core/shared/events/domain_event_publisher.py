
from __future__ import annotations

from typing import Protocol

from src.core.shared.events.domain_event import DomainEvent
from src.core.shared.events.domain_event_context import DomainEventContext

# `UnitOfWork` is defined in P3 (src/core/shared/persistence/unit_of_work.py), which does not
# exist yet -- P1 must not depend on it. Referenced below as a bare forward reference only:
# `from __future__ import annotations` makes every annotation in this module a lazy string, so
# this name is never resolved (no NameError) unless something calls typing.get_type_hints() on
# these Protocols, which nothing in P1 does. No import of a nonexistent module is needed.


class TransactionalEventDispatcher(Protocol):
    def dispatch(self, event: DomainEvent, uow: UnitOfWork) -> None: ...


class PostCommitEventPublisher(Protocol):
    def publish(self, event: DomainEvent, context: DomainEventContext) -> None: ...


__all__ = ["TransactionalEventDispatcher", "PostCommitEventPublisher"]
