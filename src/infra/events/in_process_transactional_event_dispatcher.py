"""ADR-005 §7: the concrete, in-process `TransactionalEventDispatcher`.

Stateless across dispatch calls -- no queue, no `_dispatching` flag. Handler dispatch is
synchronous, pre-commit, FAIL_FAST: an exception from any handler propagates immediately out of
`dispatch()`, and the remaining registered handlers for that call do not run. This dispatcher
does not decide rollback itself -- it only propagates, so a future `UnitOfWork` (P3) can roll
back the transaction it owns.

Deliberately transaction-neutral: this file does not create a SQLAlchemy `Session`, does not
commit, does not roll back, does not open a transaction, and does not import `sqlalchemy` at
all. `uow` is accepted and forwarded to handlers exactly as given -- this dispatcher never
inspects it, matching ADR-005 §9's guarantee that `UnitOfWork` is not yet a concrete type this
package needs to know the shape of.

Handler matching is by exact event type only (`type(event)`), never a subclass/MRO-based match
-- ADR-005's own Test Impact section states this explicitly ("Handler dispatch is by exact event
type only"), and Alternatives Rejected rules out polymorphic/supertype subscription for the same
reason: it would create double-dispatch ambiguity.
"""

from __future__ import annotations

from threading import RLock

from src.core.shared.events.domain_event import DomainEvent
from src.core.shared.events.domain_event_publisher import TransactionalEventDispatcher
from src.core.shared.events.domain_event_subscriber import (
    TransactionalEventHandler,
    TransactionalEventSubscriber,
)
from src.core.shared.events.subscription import Subscription


class InProcessTransactionalEventDispatcher(TransactionalEventDispatcher, TransactionalEventSubscriber):
    def __init__(self) -> None:
        self._handlers: dict[type, list[TransactionalEventHandler]] = {}
        self._lock = RLock()

    def subscribe(
        self, event_type: type, handler: TransactionalEventHandler
    ) -> Subscription:
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)
        return _TransactionalSubscription(self, event_type, handler)

    def dispatch(self, event: DomainEvent, uow) -> None:  # noqa: ANN001 -- uow: UnitOfWork (P3, forward reference only)
        with self._lock:
            handlers = tuple(self._handlers.get(type(event), ()))
        for handler in handlers:
            handler(event, uow)  # FAIL_FAST -- propagates straight out, no try/except here

    def _remove(self, event_type: type, handler: TransactionalEventHandler) -> None:
        with self._lock:
            registered = self._handlers.get(event_type)
            if registered is not None and handler in registered:
                registered.remove(handler)


class _TransactionalSubscription:
    """Identity-safe: disposing one subscription never affects another subscription that
    happens to have registered an identical (event_type, handler) pair -- each subscribe()
    call is independent, matching this bus's own list-based (not set-based) registry, and
    dispose() is idempotent (safe to call more than once), matching the legacy Signal's own
    already-idempotent disconnect() behavior in this codebase.
    """

    def __init__(
        self,
        dispatcher: InProcessTransactionalEventDispatcher,
        event_type: type,
        handler: TransactionalEventHandler,
    ) -> None:
        self._dispatcher = dispatcher
        self._event_type = event_type
        self._handler = handler
        self._disposed = False

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        self._dispatcher._remove(self._event_type, self._handler)


__all__ = ["InProcessTransactionalEventDispatcher"]
