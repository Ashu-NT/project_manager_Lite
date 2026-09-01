from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.core.modules.project_management.application.financials.rate_cards.event_handlers.view_invalidation import (
    RATE_CARD_CATEGORY,
    RATE_CARD_DETAIL_SCOPE_CODE,
    RATE_CARD_LIST_SCOPE_CODE,
)
from src.core.shared.events.view_invalidation import (
    ExactOrganization,
    OrganizationScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)
from src.ui_qml.platform.adapters.scoped_view_invalidation_subscription import (
    ScopedViewInvalidationSubscription,
)


class RateCardViewInvalidationAdapter(QObject):
    rateCardListStale = Signal(str)  # rate_card_id -- organization-wide card, every project may refresh
    rateCardListStaleForProject = Signal(str)  # project_id -- project-specific card, that project only
    rateCardDetailStale = Signal(str)  # rate_card_id

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
        if hint.category != RATE_CARD_CATEGORY:
            return
        if hint.scope_code == RATE_CARD_LIST_SCOPE_CODE:
            if isinstance(hint.scope, OrganizationScope):
                self.rateCardListStale.emit(hint.entity_id or "")
            else:
                self.rateCardListStaleForProject.emit(hint.entity_id or "")
        elif hint.scope_code == RATE_CARD_DETAIL_SCOPE_CODE:
            self.rateCardDetailStale.emit(hint.entity_id or "")

    def dispose(self) -> None:
        self._subscription.dispose()


__all__ = ["RateCardViewInvalidationAdapter"]
