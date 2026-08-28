"""P5A + Organization-specific P6A cutover: the Qt adapter translating `OrganizationCreated`'s
`ViewInvalidationHint`s (transport-independent) into a presentation-friendly Qt signal.

Architectural boundary this file exists to preserve:

    Domain/Application -> ViewInvalidationChannel -> Qt adapter (here) -> controller/presenter

Controllers/presenters connected to `organizationCollectionStale` know nothing about
`DomainEvent`, `OrganizationCreated`, `PostCommitEventPublisher`, `EventScope`, or `ScopeFilter`
-- they only know "the organization collection I read is stale," exactly the same shape of fact
a future SSE/WebSocket adapter would translate for a web client from the identical
`ViewInvalidationHint`. Only the Organization "organization_list" target is wired to a Qt
consumer here -- the "organization_details" target `platform_p5_event_discovery.md` also
documents has no current UI consumer (confirmed by tracing both real consumer chains) and is
deliberately left unconsumed; wiring it now would add a UI reaction with nothing to verify it
against. Its scope (`OrganizationScope(tenant_id, organization_id)`) is preserved unchanged in
the mapper for whenever a future consumer needs it -- this adapter does not touch that path.

Tenant scoping (hardened after review): subscribes via the canonical `TenantWide(tenant_id)`
`ScopeFilter` for whichever tenant is currently active, not `AllTenants()`. An `AllTenants()`
subscription was the original choice -- reasoned (incorrectly, per review) as "safe" because the
eventual desktop-API re-fetch this signal triggers is itself always tenant-scoped, so no *wrong*
data could ever reach the UI. That reasoning missed ADR-005's actual requirement: the
*invalidation signal itself* must not fire for a tenant the UI isn't currently showing, not just
the eventual read. A single `PlatformWorkspaceCatalog`/adapter instance persists across a tenant
switch in this desktop process (confirmed: `TenantSwitcherController.switchToTenant()` mutates
the backend's active-tenant state in place and never reconstructs the QML controller tree), so
`set_active_tenant(...)` must be re-invoked on switch -- wired to
`TenantSwitcherController.tenantSwitched` in `context.py`. Each call disposes the previous
subscription before creating the new one: at most one live subscription at any time, no stale
Tenant A registration surviving a switch to Tenant B, no duplicate callbacks.

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
    TenantWide,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)
from src.ui_qml.platform.adapters.scoped_view_invalidation_subscription import (
    ScopedViewInvalidationSubscription,
)


class OrganizationViewInvalidationAdapter(QObject):
    """Emits `organizationCollectionStale` whenever the organization collection ViewInvalidation
    target fires for the currently active tenant. Construct with `channel=None` (e.g. a QML
    preview with no backend connected) to no-op -- matches every other adapter/presenter in this
    codebase that degrades gracefully when its backing API isn't wired. Construct with
    `tenant_id=""` (no tenant resolvable yet) to the same effect: `TenantWide("")` never matches
    a real organization's tenant_id, so the subscription is inert until `set_active_tenant(...)`
    supplies a real one."""

    organizationCollectionStale = Signal()

    def __init__(
        self,
        *,
        channel: ViewInvalidationChannel | None,
        tenant_id: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._subscription = ScopedViewInvalidationSubscription(channel=channel, on_hint=self._on_hint)
        self.set_active_tenant(tenant_id)

    def set_active_tenant(self, tenant_id: str) -> None:
        """Re-scope the live subscription to `tenant_id` -- call whenever the desktop session's
        active tenant changes (`TenantSwitcherController.tenantSwitched`). Disposes the previous
        subscription first: at most one live subscription at any time."""
        self._subscription.replace_filter(TenantWide(tenant_id) if tenant_id else None)

    def _on_hint(self, hint: ViewInvalidationHint) -> None:
        if hint.category == ORGANIZATION_CATEGORY and hint.scope_code == ORGANIZATION_LIST_SCOPE_CODE:
            self.organizationCollectionStale.emit()

    def dispose(self) -> None:
        self._subscription.dispose()


__all__ = ["OrganizationViewInvalidationAdapter"]
