"""ADR-005 §8: the concrete, in-process `PostCommitEventPublisher`.

Queued, race-fixed, handler-snapshot-safe, ISOLATE_AND_CONTINUE, explicitly breadth-first.

Breadth-first is a deliberate design choice (ADR-005 §8), not a preservation of the legacy
`Signal` primitive's accidental depth-first-under-recursion behavior (pinned down by P0's
characterization test). If a handler for event A re-entrantly calls `publish(eventB, ...)`,
event B's handlers run only after ALL of event A's handlers have finished -- this falls out
naturally from the queue+drain algorithm below, not from any special-casing.

Race fix: the empty-queue check and the `_dispatching` flip to False happen in the SAME
critical section. A `publish()` arriving between those two statements is impossible: it either
completes its own append+check before that block runs (and the block then sees a non-empty
queue and keeps looping), or it runs after the block has already flipped `_dispatching` to
False (and correctly starts its own new drain).

Handler-registry snapshot is taken under the same lock `subscribe()`/dispose() use -- a
concurrent subscribe()/dispose() is never observed mid-iteration.

ISOLATE_AND_CONTINUE: one handler's exception is caught and logged with enough context to
diagnose it (event type, handler identity, correlation_id from the passed `DomainEventContext`,
plus tenant_id/organization_id read defensively via getattr(), since a generic `DomainEvent`
Protocol makes no promise those fields exist) -- it never propagates, and never blocks a sibling
handler or a later event in the same drain. Only `Exception` is caught, never `BaseException` --
process-control signals (`KeyboardInterrupt`, `SystemExit`) are not `Exception` subclasses and
are never swallowed here.

Deliberately transaction-neutral: no SQLAlchemy, no session, no commit/rollback. This bus does
not know or care whether a database commit actually happened -- a future `UnitOfWork` (P3) is
the only thing that calls `publish()`, and only after its own commit succeeds.
"""

from __future__ import annotations

import logging
from collections import deque
from threading import RLock

from src.core.shared.events.domain_event import DomainEvent
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_event_publisher import PostCommitEventPublisher
from src.core.shared.events.domain_event_subscriber import (
    PostCommitEventHandler,
    PostCommitEventSubscriber,
)
from src.core.shared.events.subscription import Subscription

logger = logging.getLogger(__name__)


class InProcessPostCommitEventBus(PostCommitEventPublisher, PostCommitEventSubscriber):
    def __init__(self) -> None:
        self._handlers: dict[type, list[PostCommitEventHandler]] = {}
        self._queue: deque[tuple[DomainEvent, DomainEventContext]] = deque()
        self._dispatching = False
        self._lock = RLock()

    def subscribe(
        self, event_type: type, handler: PostCommitEventHandler
    ) -> Subscription:
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)
        return _PostCommitSubscription(self, event_type, handler)

    def publish(self, event: DomainEvent, context: DomainEventContext) -> None:
        with self._lock:
            self._queue.append((event, context))
            if self._dispatching:
                return
            self._dispatching = True
        self._drain()

    def _drain(self) -> None:
        while True:
            with self._lock:
                if not self._queue:
                    # Empty-check and the "no longer dispatching" flip happen atomically,
                    # in the SAME critical section -- see module docstring for why this is
                    # the race fix.
                    self._dispatching = False
                    return
                current_event, current_context = self._queue.popleft()
            self._dispatch_one(current_event, current_context)  # never called while holding _lock

    def _dispatch_one(self, event: DomainEvent, context: DomainEventContext) -> None:
        with self._lock:
            handlers = tuple(self._handlers.get(type(event), ()))
        for handler in handlers:
            try:
                handler(event, context)
            except Exception:
                logger.exception(
                    "Post-commit handler failed",
                    extra={
                        "event_type": type(event).__name__,
                        "handler": getattr(handler, "__qualname__", repr(handler)),
                        "correlation_id": context.correlation_id,
                        "causation_id": context.causation_id,
                        "command_id": context.command_id,
                        "tenant_id": getattr(event, "tenant_id", None),
                        "organization_id": getattr(event, "organization_id", None),
                    },
                )

    def _remove(self, event_type: type, handler: PostCommitEventHandler) -> None:
        with self._lock:
            registered = self._handlers.get(event_type)
            if registered is not None and handler in registered:
                registered.remove(handler)


class _PostCommitSubscription:
    """Idempotent dispose(), independent of any other subscription -- see the identical
    rationale on `_TransactionalSubscription`."""

    def __init__(
        self,
        bus: InProcessPostCommitEventBus,
        event_type: type,
        handler: PostCommitEventHandler,
    ) -> None:
        self._bus = bus
        self._event_type = event_type
        self._handler = handler
        self._disposed = False

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        self._bus._remove(self._event_type, self._handler)


__all__ = ["InProcessPostCommitEventBus"]
