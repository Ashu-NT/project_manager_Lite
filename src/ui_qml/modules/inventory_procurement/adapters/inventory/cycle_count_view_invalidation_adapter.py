from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.core.modules.inventory_procurement.application.inventory.event_handlers.view_invalidation import (
    CYCLE_COUNT_CATEGORY,
    CYCLE_COUNT_DETAIL_SCOPE_CODE,
    CYCLE_COUNT_LIST_SCOPE_CODE,
)
from src.core.shared.events.view_invalidation import (
    ExactOrganization,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)
from src.ui_qml.shared.adapters.scoped_view_invalidation_subscription import (
    ScopedViewInvalidationSubscription,
)


class CycleCountViewInvalidationAdapter(QObject):
    cycleCountListStale = Signal(str)  # cycle_count_id
    cycleCountDetailStale = Signal(str)  # cycle_count_id

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
        if hint.category != CYCLE_COUNT_CATEGORY:
            return
        if hint.scope_code == CYCLE_COUNT_LIST_SCOPE_CODE:
            self.cycleCountListStale.emit(hint.entity_id or "")
        elif hint.scope_code == CYCLE_COUNT_DETAIL_SCOPE_CODE:
            self.cycleCountDetailStale.emit(hint.entity_id or "")

    def dispose(self) -> None:
        self._subscription.dispose()


__all__ = ["CycleCountViewInvalidationAdapter"]
