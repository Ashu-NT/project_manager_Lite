from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.core.modules.project_management.application.financials.financial_changes.event_handlers.view_invalidation import (
    FINANCIAL_CHANGE_BUDGET_SCOPE_CODE,
    FINANCIAL_CHANGE_CATEGORY,
    FINANCIAL_CHANGE_FORECAST_SCOPE_CODE,
    FINANCIAL_CHANGE_SCHEDULE_SCOPE_CODE,
    FINANCIAL_CHANGE_WORKSPACE_SCOPE_CODE,
)
from src.core.shared.events.view_invalidation import (
    ExactOrganization,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)
from src.ui_qml.shared.adapters.scoped_view_invalidation_subscription import (
    ScopedViewInvalidationSubscription,
)


class FinancialChangeViewInvalidationAdapter(QObject):
    workspaceStale = Signal(str)
    budgetBasisStale = Signal(str)
    forecastBasisStale = Signal(str)
    scheduleStale = Signal(str)

    def __init__(
        self,
        *,
        channel: ViewInvalidationChannel | None,
        tenant_id: str,
        organization_id: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._subscription = ScopedViewInvalidationSubscription(
            channel=channel, on_hint=self._on_hint
        )
        self.set_active_scope(tenant_id=tenant_id, organization_id=organization_id)

    def set_active_scope(self, *, tenant_id: str, organization_id: str) -> None:
        self._subscription.replace_filter(
            ExactOrganization(tenant_id, organization_id)
            if tenant_id and organization_id
            else None
        )

    def _on_hint(self, hint: ViewInvalidationHint) -> None:
        if hint.category != FINANCIAL_CHANGE_CATEGORY:
            return
        signal_by_scope = {
            FINANCIAL_CHANGE_WORKSPACE_SCOPE_CODE: self.workspaceStale,
            FINANCIAL_CHANGE_BUDGET_SCOPE_CODE: self.budgetBasisStale,
            FINANCIAL_CHANGE_FORECAST_SCOPE_CODE: self.forecastBasisStale,
            FINANCIAL_CHANGE_SCHEDULE_SCOPE_CODE: self.scheduleStale,
        }
        signal = signal_by_scope.get(hint.scope_code)
        if signal is not None:
            signal.emit(hint.entity_id or "")

    def dispose(self) -> None:
        self._subscription.dispose()


__all__ = ["FinancialChangeViewInvalidationAdapter"]
