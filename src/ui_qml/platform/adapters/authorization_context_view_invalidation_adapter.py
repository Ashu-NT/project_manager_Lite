from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.core.platform.application.security.authorization.roles.event_handlers.view_invalidation import (
    AUTHORIZATION_CONTEXT_CATEGORY,
    AUTHORIZATION_CONTEXT_SCOPE_CODE,
)
from src.core.shared.events.view_invalidation import (
    TenantWide,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)
from src.ui_qml.shared.adapters.scoped_view_invalidation_subscription import (
    ScopedViewInvalidationSubscription,
)


class AuthorizationContextViewInvalidationAdapter(QObject):
    """Emits `authorizationContextStale` whenever the `authorization_context` ViewInvalidation
    target fires for the currently active tenant -- custom-Role create/update/retire and
    system role-policy reconciliation. Distinct from `RoleBindingViewInvalidationAdapter`'s own
    `roleBindingsStale` (RoleBinding grant/revoke), which covers the other half of "does the
    viewer's own authority need re-evaluation" without overlap. Construct with `channel=None`
    (e.g. a QML preview with no backend connected) to no-op."""

    authorizationContextStale = Signal()

    def __init__(
        self,
        *,
        channel: ViewInvalidationChannel | None,
        tenant_id: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._tenant_subscription = ScopedViewInvalidationSubscription(channel=channel, on_hint=self._on_hint)
        self.set_active_scope(tenant_id=tenant_id)

    def set_active_scope(self, *, tenant_id: str) -> None:
        self._tenant_subscription.replace_filter(TenantWide(tenant_id) if tenant_id else None)

    def _on_hint(self, hint: ViewInvalidationHint) -> None:
        if hint.category == AUTHORIZATION_CONTEXT_CATEGORY and hint.scope_code == AUTHORIZATION_CONTEXT_SCOPE_CODE:
            self.authorizationContextStale.emit()

    def dispose(self) -> None:
        self._tenant_subscription.dispose()


__all__ = ["AuthorizationContextViewInvalidationAdapter"]
