from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.core.platform.application.master_data.documents.event_handlers.view_invalidation import (
    DOCUMENT_CATEGORY,
    DOCUMENT_LINKS_SCOPE_CODE,
)
from src.core.shared.events.view_invalidation import (
    ExactOrganization,
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)
from src.ui_qml.shared.adapters.scoped_view_invalidation_subscription import (
    ScopedViewInvalidationSubscription,
)


class DocumentLinksViewInvalidationAdapter(QObject):
    """Org-scoped only at the channel level -- exactly like every other adapter. Unlike them,
    `document_links` hints target one specific business entity (or, in the reverse shape, one
    specific document) rather than "the whole list," so per-target filtering happens in the
    consumer's own slot (comparing against whatever it currently has selected/open), not here.
    This mirrors how "currently selected" state already lives in the consuming controller, not
    in the adapter -- no per-entity re-scoping plumbing is needed as the selection changes."""

    documentLinksStale = Signal(str, str, str)  # module_code ("" if none), entity_type, entity_id

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
        if hint.category == DOCUMENT_CATEGORY and hint.scope_code == DOCUMENT_LINKS_SCOPE_CODE:
            module_code = hint.scope.module_code if isinstance(hint.scope, ResourceScope) else ""
            self.documentLinksStale.emit(module_code, hint.entity_type, hint.entity_id or "")

    def dispose(self) -> None:
        self._subscription.dispose()


__all__ = ["DocumentLinksViewInvalidationAdapter"]
