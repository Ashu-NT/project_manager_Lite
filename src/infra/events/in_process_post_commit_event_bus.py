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
