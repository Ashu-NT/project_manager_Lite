"""P5A + Organization-specific P6A cutover: the Qt adapter translating `OrganizationCreated`'s
`ViewInvalidationHint`s (transport-independent) into a presentation-friendly Qt signal.

Architectural boundary this file exists to preserve:

    Domain/Application -> ViewInvalidationChannel -> Qt adapter (here) -> controller/presenter

Controllers/presenters connected to `organizationCollectionStale` know nothing about
`DomainEvent`, `OrganizationCreated`, `PostCommitEventPublisher`, or `ScopeFilter` -- they only
know "the organization collection I read is stale," exactly the same shape of fact a future
SSE/WebSocket adapter would translate for a web client from the identical
`ViewInvalidationHint`. Only the Organization "organization_list" target is wired to a Qt
consumer here -- the "organization_details" target `platform_p5_event_discovery.md` also
documents has no current UI consumer (confirmed by tracing both real consumer chains) and is
deliberately left unconsumed; wiring it now would add a UI reaction with nothing to verify it
against.

Subscribes via the existing `AllTenants()` `ScopeFilter` (P1/P2 -- no new filter kind invented
here): this desktop process holds exactly one active session/tenant at a time, and both
consumers (the admin console organization list, the settings organization-profiles list) are
platform-admin-only screens (`AllTenants` is documented as "platform-admin-only" in
`src/core/shared/events/view_invalidation.py`) that re-fetch through their own, already
tenant-scoped desktop API call regardless of which hint triggered the refresh -- the adapter
only decides *whether* to ask for a re-fetch, never *which* tenant's data to show.

Thread safety: `InProcessPostCommitEventBus`/`InProcessViewInvalidationChannel` are synchronous,
in-process, same-thread callback mechanisms (see their own module docstrings) -- this adapter's
`_on_hint` runs on whatever thread called `uow.commit()`, which in this desktop application is
always the Qt main thread (every backend call originates from a QML `Slot` handler). Emitting a
Qt signal from that same thread is a direct connection, exactly the pattern this codebase's
existing controllers already use for their own synchronous `*Changed.emit()` calls -- no
QTimer-based polling, no additional threading infrastructure.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.core.platform.application.master_data.org.event_handlers.view_invalidation import (
    ORGANIZATION_CATEGORY,
    ORGANIZATION_LIST_SCOPE_CODE,
)
from src.core.shared.events.view_invalidation import (
    AllTenants,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)


class OrganizationViewInvalidationAdapter(QObject):
    """Emits `organizationCollectionStale` whenever the organization collection ViewInvalidation
    target fires. Construct with `channel=None` (e.g. a QML preview with no backend connected)
    to no-op -- matches every other adapter/presenter in this codebase that degrades gracefully
    when its backing API isn't wired."""

    organizationCollectionStale = Signal()

    def __init__(
        self,
        *,
        channel: ViewInvalidationChannel | None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._subscription = (
            channel.subscribe(AllTenants(), self._on_hint) if channel is not None else None
        )

    def _on_hint(self, hint: ViewInvalidationHint) -> None:
        if hint.category == ORGANIZATION_CATEGORY and hint.scope_code == ORGANIZATION_LIST_SCOPE_CODE:
            self.organizationCollectionStale.emit()

    def dispose(self) -> None:
        if self._subscription is not None:
            self._subscription.dispose()
            self._subscription = None


__all__ = ["OrganizationViewInvalidationAdapter"]
