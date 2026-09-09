from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.core.platform.application.security.auth.event_handlers.view_invalidation import (
    ACCOUNT_SECURITY_CATEGORY,
    ACCOUNT_SECURITY_SCOPE_CODE,
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


class AccountSecurityViewInvalidationAdapter(QObject):
    """Emits `accountSecurityStale` whenever the `account_security` ViewInvalidation target
    fires for the currently active tenant, or platform-wide for a tenant-less (platform) account.
    Construct with `channel=None` (e.g. a QML preview with no backend connected) to no-op."""

    accountSecurityStale = Signal()

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
        self._tenant_subscription.replace_filter(TenantWide(tenant_id) if tenant_id else None)
        self._organization_subscription.replace_filter(
            ExactOrganization(tenant_id, organization_id) if tenant_id and organization_id else None
        )

    def _on_hint(self, hint: ViewInvalidationHint) -> None:
        if hint.category == ACCOUNT_SECURITY_CATEGORY and hint.scope_code == ACCOUNT_SECURITY_SCOPE_CODE:
            self.accountSecurityStale.emit()

    def dispose(self) -> None:
        self._tenant_subscription.dispose()
        self._organization_subscription.dispose()


__all__ = ["AccountSecurityViewInvalidationAdapter"]
