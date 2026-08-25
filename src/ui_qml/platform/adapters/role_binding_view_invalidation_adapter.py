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
        self._channel = channel
        self._tenant_subscription = None
        self._organization_subscription = None
        self.set_active_scope(tenant_id=tenant_id, organization_id=organization_id)

    def set_active_scope(self, *, tenant_id: str, organization_id: str) -> None:
        """Re-scope both live subscriptions to `tenant_id`/`(tenant_id, organization_id)` --
        call whenever the desktop session's active tenant or active organization changes.
        Disposes the previous subscriptions first."""
        self._dispose_subscriptions()
        if self._channel is None:
            return
        if tenant_id:
            self._tenant_subscription = self._channel.subscribe(TenantWide(tenant_id), self._on_hint)
        if tenant_id and organization_id:
            self._organization_subscription = self._channel.subscribe(
                ExactOrganization(tenant_id, organization_id), self._on_hint
            )

    def _on_hint(self, hint: ViewInvalidationHint) -> None:
        if hint.category == ROLE_BINDING_CATEGORY and hint.scope_code == ROLE_BINDING_ASSIGNMENTS_SCOPE_CODE:
            self.roleBindingsStale.emit()

    def _dispose_subscriptions(self) -> None:
        if self._tenant_subscription is not None:
            self._tenant_subscription.dispose()
            self._tenant_subscription = None
        if self._organization_subscription is not None:
            self._organization_subscription.dispose()
            self._organization_subscription = None

    def dispose(self) -> None:
        self._dispose_subscriptions()


__all__ = ["RoleBindingViewInvalidationAdapter"]
