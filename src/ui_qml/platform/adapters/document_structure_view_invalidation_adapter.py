from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.core.platform.application.master_data.documents.event_handlers.view_invalidation import (
    DOCUMENT_STRUCTURE_CATEGORY,
    DOCUMENT_STRUCTURE_LIST_SCOPE_CODE,
)
from src.core.shared.events.view_invalidation import (
    ExactOrganization,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)
from src.ui_qml.platform.adapters.scoped_view_invalidation_subscription import (
    ScopedViewInvalidationSubscription,
)


class DocumentStructureViewInvalidationAdapter(QObject):
    documentStructureCollectionStale = Signal()

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
        self._subscription.replace_filter(
            ExactOrganization(tenant_id, organization_id) if tenant_id and organization_id else None
        )

    def _on_hint(self, hint: ViewInvalidationHint) -> None:
        if hint.category == DOCUMENT_STRUCTURE_CATEGORY and hint.scope_code == DOCUMENT_STRUCTURE_LIST_SCOPE_CODE:
            self.documentStructureCollectionStale.emit()

    def dispose(self) -> None:
        self._subscription.dispose()


__all__ = ["DocumentStructureViewInvalidationAdapter"]
