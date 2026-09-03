from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.core.platform.application.security.authorization.roles.event_handlers.view_invalidation import (
    ROLE_BINDING_ASSIGNMENTS_SCOPE_CODE,
    ROLE_BINDING_CATEGORY,
)
from src.core.shared.events.view_invalidation import (
    ExactOrganization,
    TenantWide,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)
from src.ui_qml.shared.adapters.scoped_view_invalidation_subscription import (
    ScopedViewInvalidationSubscription,
)


class RoleBindingViewInvalidationAdapter(QObject):
    """Emits `roleBindingsStale` whenever the role-binding assignment ViewInvalidation target
    fires for the currently active tenant (tenant-scoped facts) or the currently active
    (tenant, organization) pair (resource-scoped facts). Construct with `channel=None` (e.g. a
    QML preview with no backend connected) to no-op."""

    roleBindingsStale = Signal()

    def __init__(
        self,
        *,
        channel: ViewInvalidationChannel | None,
        tenant_id: str,
        organization_id: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._tenant_subscription = ScopedViewInvalidationSubscription(channel=channel, on_hint=self._on_hint)
        self._organization_subscription = ScopedViewInvalidationSubscription(channel=channel, on_hint=self._on_hint)
        self.set_active_scope(tenant_id=tenant_id, organization_id=organization_id)

    def set_active_scope(self, *, tenant_id: str, organization_id: str) -> None:
        """Re-scope both live subscriptions to `tenant_id`/`(tenant_id, organization_id)` --
        call whenever the desktop session's active tenant or active organization changes.
        Disposes the previous subscriptions first. Two simultaneous subscriptions, not one --
        RoleBinding facts are polymorphically scoped (platform/tenant/resource, see the mapper's
        own `_to_event_scope`), and a tenant-scoped fact must still reach a controller that also
        cares about a specific organization's resource-scoped facts, and vice versa."""
        self._tenant_subscription.replace_filter(TenantWide(tenant_id) if tenant_id else None)
        self._organization_subscription.replace_filter(
            ExactOrganization(tenant_id, organization_id) if tenant_id and organization_id else None
        )

    def _on_hint(self, hint: ViewInvalidationHint) -> None:
        if hint.category == ROLE_BINDING_CATEGORY and hint.scope_code == ROLE_BINDING_ASSIGNMENTS_SCOPE_CODE:
            self.roleBindingsStale.emit()

    def dispose(self) -> None:
        self._tenant_subscription.dispose()
        self._organization_subscription.dispose()


__all__ = ["RoleBindingViewInvalidationAdapter"]
