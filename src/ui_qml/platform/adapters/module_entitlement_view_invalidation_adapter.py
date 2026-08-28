"""P5B-3: the Qt adapter translating the five Module Entitlement events' `ViewInvalidationHint`
(transport-independent) into a presentation-friendly Qt signal.

Architectural boundary this file exists to preserve:

    Domain/Application -> ViewInvalidationChannel -> Qt adapter (here) -> controller/presenter

Controllers/presenters connected to `moduleEntitlementsStale` know nothing about `DomainEvent`,
`ModuleLicensed`/etc., `PostCommitEventPublisher`, `EventScope`, or `ScopeFilter` -- they only know
"the module entitlement collection I read is stale," exactly the same shape of fact a future
SSE/WebSocket adapter would translate for a web client from the identical `ViewInvalidationHint`.

Organization scoping (mirrors the Organization P6A hardening review, not its `TenantWide`
subscription -- Module entitlements are organization-owned, not tenant-wide): subscribes via
`ExactOrganization(tenant_id, organization_id)` for whichever organization is currently active.
`AllTenants()`/`TenantWide(...)` are never used here -- an organization-specific read must not be
invalidated by a broader filter merely because the eventual re-fetch happens to be tenant-safe.

Tenant AND organization switch lifecycle: a single `PlatformWorkspaceCatalog`/adapter instance
persists across both kinds of switch in this desktop process (the QML controller tree is never
reconstructed), so `set_active_scope(...)` must be re-invoked on either -- wired to
`PlatformWorkspaceCatalog.refreshCurrentPermissions()` in `context.py`, the same existing hook the
QML shell already calls immediately after both a tenant switch (`ContextBar.onTenantSelected`) and
an organization switch (`ContextBar.onOrganizationSelected`) -- see `PlatformWorkspacePage.qml`.
Each call disposes the previous subscription before creating the new one: at most one live
subscription at any time, no stale Tenant-A/Organization-A1 registration surviving a switch to a
different tenant or organization, no duplicate callbacks.

Thread safety: identical to `OrganizationViewInvalidationAdapter` -- see its own docstring.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.core.platform.application.tenant.modules.event_handlers.view_invalidation import (
    MODULE_ENTITLEMENT_CATEGORY,
    MODULE_ENTITLEMENTS_SCOPE_CODE,
)
from src.core.shared.events.view_invalidation import (
    ExactOrganization,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)
from src.ui_qml.platform.adapters.scoped_view_invalidation_subscription import (
    ScopedViewInvalidationSubscription,
)


class ModuleEntitlementViewInvalidationAdapter(QObject):
    """Emits `moduleEntitlementsStale` whenever the module entitlement collection
    ViewInvalidation target fires for the currently active (tenant, organization) pair.
    Construct with `channel=None` (e.g. a QML preview with no backend connected) to no-op.
    Construct with an empty `tenant_id`/`organization_id` (no active organization resolvable yet)
    to the same effect: `ExactOrganization("", "")` never matches a real event's scope, so the
    subscription is inert until `set_active_scope(...)` supplies real values."""

    moduleEntitlementsStale = Signal()

    def __init__(
        self,
        *,
        channel: ViewInvalidationChannel | None,
        tenant_id: str,
        organization_id: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._subscription = ScopedViewInvalidationSubscription(channel=channel, on_hint=self._on_hint)
        self.set_active_scope(tenant_id=tenant_id, organization_id=organization_id)

    def set_active_scope(self, *, tenant_id: str, organization_id: str) -> None:
        """Re-scope the live subscription to `(tenant_id, organization_id)` -- call whenever the
        desktop session's active tenant or active organization changes. Disposes the previous
        subscription first: at most one live subscription at any time."""
        self._subscription.replace_filter(
            ExactOrganization(tenant_id, organization_id) if tenant_id and organization_id else None
        )

    def _on_hint(self, hint: ViewInvalidationHint) -> None:
        if hint.category == MODULE_ENTITLEMENT_CATEGORY and hint.scope_code == MODULE_ENTITLEMENTS_SCOPE_CODE:
            self.moduleEntitlementsStale.emit()

    def dispose(self) -> None:
        self._subscription.dispose()


__all__ = ["ModuleEntitlementViewInvalidationAdapter"]
