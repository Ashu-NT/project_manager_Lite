from __future__ import annotations

import itertools
import logging
from threading import RLock

from src.core.shared.events.subscription import Subscription
from src.core.shared.events.view_invalidation import (
    ScopeFilter,
    ViewInvalidationChannel,
    ViewInvalidationHandler,
    ViewInvalidationHint,
)

logger = logging.getLogger(__name__)


class InProcessViewInvalidationChannel(ViewInvalidationChannel):
    def __init__(self) -> None:
        self._subscriptions: dict[int, tuple[ScopeFilter, ViewInvalidationHandler]] = {}
        self._next_id = itertools.count()
        self._lock = RLock()

    def subscribe(
        self,
        filter: ScopeFilter,
        handler: ViewInvalidationHandler[ViewInvalidationHint],
    ) -> Subscription:
        subscription_id = next(self._next_id)
        with self._lock:
            self._subscriptions[subscription_id] = (filter, handler)
        return _ViewInvalidationSubscription(self, subscription_id)

    def notify(self, hint: ViewInvalidationHint) -> None:
        with self._lock:
            snapshot = tuple(self._subscriptions.values())
        for filt, handler in snapshot:
            if not filt.matches(hint.scope):
                continue
            try:
                handler(hint)
            except Exception:
                logger.exception(
                    "View invalidation subscriber failed",
                    extra={
                        "scope": repr(hint.scope),
                        "category": hint.category,
                        "scope_code": hint.scope_code,
                        "entity_type": hint.entity_type,
                        "entity_id": hint.entity_id,
                        "handler": getattr(handler, "__qualname__", repr(handler)),
                    },
                )

    def _remove(self, subscription_id: int) -> None:
        with self._lock:
            self._subscriptions.pop(subscription_id, None)


class _ViewInvalidationSubscription:
    def __init__(self, channel: InProcessViewInvalidationChannel, subscription_id: int) -> None:
        self._channel = channel
        self._subscription_id = subscription_id
        self._disposed = False

    def dispose(self) -> None:
        if self._disposed:
            return
        self._disposed = True
        self._channel._remove(self._subscription_id)


__all__ = ["InProcessViewInvalidationChannel"]
