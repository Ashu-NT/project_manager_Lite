"""ADR-005 §9: `UnitOfWork`/`UnitOfWorkFactory` protocols.

"Unit of Work" is reserved to mean exactly one thing in this codebase going forward: one
physical database transaction, owning one fresh `Session`, owning commit/rollback, owning the
event collection/dispatch lifecycle for that transaction. Not a helper around any existing
process-lifetime `Session`, and not a logical commit convention layered over a shared session
(see ADR-005 §9's rationale, and §24's reconciliation with `ApprovalService`'s existing,
narrower pattern -- a P4+ concern, not decided or touched here).

No `session` field, no repository accessors on this shared protocol -- a module/capability
-specific extension (e.g. `ProjectManagementUnitOfWork(UnitOfWork, Protocol)`) adds its own
typed repository accessors, decided at that module's own migration phase (P4+). This protocol
never gains a generic `repository_for(contract)`-style lookup: an earlier draft proposed
exactly that and a critical review found it would let `UnitOfWork` become a hidden general
service locator, weakening module-boundary visibility, static enforcement, and testability.
The one genuine cross-module need this codebase has (`ApprovalService`'s apply handlers) is
resolved narrowly at ADR-005 §24, by an explicit per-handler dependency declaration -- not by
a method on `UnitOfWork` itself.

Lives under `shared/persistence/`, not `shared/events/` -- a transaction/aggregate-tracking
abstraction is not itself events-specific vocabulary, the same reasoning already applied to
`Clock` (`shared/time/`). Depends only on Core Shared event contracts (already below both
Platform and modules) and stdlib `typing` -- no SQLAlchemy, no Platform, no business module.
"""

from __future__ import annotations

from typing import Protocol

from src.core.shared.events.aggregate_events import RecordsDomainEvents
from src.core.shared.events.domain_event import DomainEvent
from src.core.shared.events.domain_event_context import DomainEventContext


class UnitOfWorkClosedError(RuntimeError):
    """Raised when a `UnitOfWork` method is called after its transaction has already ended
    (via a successful `commit()`, or a rollback triggered by `__exit__`). A new `UnitOfWork`
    must be created for further work -- this one's aggregate instances may not reflect what
    was actually persisted (ADR-005 §9's rollback-safety rule) and must never be reused."""


class MaxDispatchRoundsExceededError(RuntimeError):
    """Raised when transactional event dispatch does not quiesce within the configured round
    limit. A real cycle in event-recording handlers is a bug, not a hang (ADR-005 §10)."""


class UnitOfWork(Protocol):
    context: DomainEventContext

    def __enter__(self) -> "UnitOfWork": ...

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
