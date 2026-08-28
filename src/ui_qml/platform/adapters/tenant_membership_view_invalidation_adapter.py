from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.core.platform.application.tenant.tenancy.event_handlers.view_invalidation import (
    TENANT_MEMBERSHIPS_SCOPE_CODE,
    TENANT_MEMBERSHIP_CATEGORY,
)
from src.core.shared.events.view_invalidation import (
    TenantWide,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)
from src.ui_qml.platform.adapters.scoped_view_invalidation_subscription import (
    ScopedViewInvalidationSubscription,
)


class TenantMembershipViewInvalidationAdapter(QObject):
    """Emits `membershipDataStale` whenever the tenant-membership ViewInvalidation target fires
    for the currently active tenant. Construct with `channel=None` (e.g. a QML preview with no
    backend connected) to no-op -- matches every other adapter/presenter in this codebase that
    degrades gracefully when its backing API isn't wired. Construct with `tenant_id=""` (no
    tenant resolvable yet) to the same effect: `TenantWide("")` never matches a real membership's
    tenant_id, so the subscription is inert until `set_active_tenant(...)` supplies a real one."""

    membershipDataStale = Signal()

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
        subscription first: at most one live subscription at any time. Deliberately NOT called
        on an organization switch -- see the module docstring."""
        self._subscription.replace_filter(TenantWide(tenant_id) if tenant_id else None)

    def _on_hint(self, hint: ViewInvalidationHint) -> None:
        if hint.category == TENANT_MEMBERSHIP_CATEGORY and hint.scope_code == TENANT_MEMBERSHIPS_SCOPE_CODE:
            self.membershipDataStale.emit()

    def dispose(self) -> None:
        self._subscription.dispose()


__all__ = ["TenantMembershipViewInvalidationAdapter"]
