from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.core.shared.events.view_invalidation import (
    ExactOrganization,
    TenantWide,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)
from src.ui_qml.shared.adapters.scoped_view_invalidation_subscription import (
    ScopedViewInvalidationSubscription,
)


class ActionCenterViewInvalidationAdapter(QObject):
    """Translate scoped committed hints; contributor targets are supplied by composition."""

    actionsStale = Signal()

    def __init__(self, *, channel: ViewInvalidationChannel | None,
                 targets: frozenset[tuple[str, str]], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._targets = targets
        self._organization = ScopedViewInvalidationSubscription(channel=channel, on_hint=self._on_hint)
        self._tenant = ScopedViewInvalidationSubscription(channel=channel, on_hint=self._on_hint)

    def set_active_scope(self, *, tenant_id: str, organization_id: str) -> None:
        self._organization.replace_filter(ExactOrganization(tenant_id, organization_id)
                                          if tenant_id and organization_id else None)
        self._tenant.replace_filter(TenantWide(tenant_id) if tenant_id else None)

    def _on_hint(self, hint: ViewInvalidationHint) -> None:
        if (hint.category, hint.scope_code) in self._targets:
            self.actionsStale.emit()

    def dispose(self) -> None:
        self._organization.dispose()
        self._tenant.dispose()
