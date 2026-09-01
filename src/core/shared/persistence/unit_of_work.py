from __future__ import annotations

from typing import Protocol, Self

from src.core.shared.events.aggregate_events import RecordsDomainEvents
from src.core.shared.events.domain_event import DomainEvent
from src.core.shared.events.domain_event_context import DomainEventContext


class UnitOfWorkClosedError(RuntimeError):
    """Raised when a `UnitOfWork` method is called after its transaction has already ended
    (via a successful `commit()`, or a rollback triggered by `__exit__`). A new `UnitOfWork`
    must be created for further work"""


class MaxDispatchRoundsExceededError(RuntimeError):
    """Raised when transactional event dispatch does not quiesce within the configured round limit."""


class UnitOfWork(Protocol):
    context: DomainEventContext

    def __enter__(self) -> Self: ...

    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...

    def register_touched(self, aggregate: RecordsDomainEvents) -> None: ...

    def record_event(self, event: DomainEvent) -> None: ...

    def tracked_aggregates(self) -> tuple[RecordsDomainEvents, ...]: ...

    def commit(self) -> None: ...


class UnitOfWorkFactory(Protocol):
    def create(self, *, context: DomainEventContext) -> UnitOfWork: ...


__all__ = [
    "UnitOfWork",
    "UnitOfWorkFactory",
    "UnitOfWorkClosedError",
    "MaxDispatchRoundsExceededError",
]
