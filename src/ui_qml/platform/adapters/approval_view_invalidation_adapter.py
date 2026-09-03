from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.core.platform.application.approval.event_handlers.view_invalidation import (
    APPROVAL_CATEGORY,
    APPROVAL_REQUESTS_SCOPE_CODE,
)
from src.core.shared.events.view_invalidation import (
    ExactOrganization,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)
from src.ui_qml.shared.adapters.scoped_view_invalidation_subscription import (
    ScopedViewInvalidationSubscription,
)


class ApprovalViewInvalidationAdapter(QObject):
    """Emits `approvalsStale` whenever the approval-request collection ViewInvalidation target
    fires for the currently active (tenant, organization) pair. Construct with `channel=None`
    (e.g. a QML preview with no backend connected) to no-op. Construct with an empty
    `tenant_id`/`organization_id` (no active organization resolvable yet) to the same effect:
    `ExactOrganization("", "")` never matches a real event's scope, so the subscription is inert
    until `set_active_scope(...)` supplies real values."""

    approvalsStale = Signal()

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
        if hint.category == APPROVAL_CATEGORY and hint.scope_code == APPROVAL_REQUESTS_SCOPE_CODE:
            self.approvalsStale.emit()

    def dispose(self) -> None:
        self._subscription.dispose()


__all__ = ["ApprovalViewInvalidationAdapter"]
