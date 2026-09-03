from __future__ import annotations

from collections.abc import Callable

from src.core.shared.events.subscription import Subscription
from src.core.shared.events.view_invalidation import (
    ScopeFilter,
    ViewInvalidationChannel,
    ViewInvalidationHandler,
    ViewInvalidationHint,
)


class ScopedViewInvalidationSubscription:
    """One live `ViewInvalidationChannel` subscription, re-scoped in place. Not a `QObject` --
    owned by (composed into) a capability-specific Qt adapter, never subclassed by one."""

    def __init__(
        self,
        *,
        channel: ViewInvalidationChannel | None,
        on_hint: ViewInvalidationHandler[ViewInvalidationHint] | Callable[[ViewInvalidationHint], None],
    ) -> None:
        self._channel = channel
        self._on_hint = on_hint
        self._subscription: Subscription | None = None

    def replace_filter(self, filter: ScopeFilter | None) -> None:
        """Dispose the previous subscription (if any), then subscribe via `filter` -- unless
        `filter` is None, in which case this goes inert (no live subscription) until the next
        call supplies a real one. Always unconditional: never skips the dispose/resubscribe cycle
        even if `filter` is equal to what was already active (see module docstring)."""
        self.dispose()
        if self._channel is not None and filter is not None:
            self._subscription = self._channel.subscribe(filter, self._on_hint)

    def dispose(self) -> None:
        """Safe to call repeatedly (including with no live subscription): a no-op after the
        first call, matching `InProcessViewInvalidationChannel`'s own subscription `dispose()`
        idempotence."""
        if self._subscription is not None:
            self._subscription.dispose()
            self._subscription = None


__all__ = ["ScopedViewInvalidationSubscription"]
