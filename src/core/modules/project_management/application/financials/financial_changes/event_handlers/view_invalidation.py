from __future__ import annotations

from src.core.modules.project_management.application.financials.financial_changes.financial_change_events import (
    FinancialChangeChanged,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

FINANCIAL_CHANGE_CATEGORY = "financial_change"
FINANCIAL_CHANGE_WORKSPACE_SCOPE_CODE = "financial_change_workspace"
FINANCIAL_CHANGE_BUDGET_SCOPE_CODE = "financial_change_budget_basis"
FINANCIAL_CHANGE_FORECAST_SCOPE_CODE = "financial_change_forecast_basis"
FINANCIAL_CHANGE_SCHEDULE_SCOPE_CODE = "financial_change_schedule"
FINANCIAL_CHANGE_MODULE_CODE = "project_management"
FINANCIAL_CHANGE_PROJECT_ENTITY_TYPE = "project"


def build_financial_change_view_invalidation_handler(
    channel: ViewInvalidationChannel,
):
    current_correlation_id: list[str | None] = [None]
    notified: set[tuple[str, str, str, str]] = set()

    def notify(event: FinancialChangeChanged, scope_code: str) -> None:
        target = (
            scope_code,
            event.tenant_id,
            event.organization_id,
            event.project_id,
        )
        if target in notified:
            return
        notified.add(target)
        channel.notify(
            ViewInvalidationHint(
                scope=ResourceScope(
                    tenant_id=event.tenant_id,
                    organization_id=event.organization_id,
                    module_code=FINANCIAL_CHANGE_MODULE_CODE,
                    entity_type=FINANCIAL_CHANGE_PROJECT_ENTITY_TYPE,
                    entity_id=event.project_id,
                ),
                category=FINANCIAL_CHANGE_CATEGORY,
                scope_code=scope_code,
                entity_type=FINANCIAL_CHANGE_PROJECT_ENTITY_TYPE,
                entity_id=event.project_id,
            )
        )

    def handle(
        event: FinancialChangeChanged, context: DomainEventContext
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified.clear()
        notify(event, FINANCIAL_CHANGE_WORKSPACE_SCOPE_CODE)
        scope_by_effect = {
            "budget": FINANCIAL_CHANGE_BUDGET_SCOPE_CODE,
            "forecast": FINANCIAL_CHANGE_FORECAST_SCOPE_CODE,
            "schedule": FINANCIAL_CHANGE_SCHEDULE_SCOPE_CODE,
        }
        for effect in event.applied_effects:
            scope_code = scope_by_effect.get(effect)
            if scope_code:
                notify(event, scope_code)

    return handle


__all__ = [
    "FINANCIAL_CHANGE_BUDGET_SCOPE_CODE",
    "FINANCIAL_CHANGE_CATEGORY",
    "FINANCIAL_CHANGE_FORECAST_SCOPE_CODE",
    "FINANCIAL_CHANGE_SCHEDULE_SCOPE_CODE",
    "FINANCIAL_CHANGE_WORKSPACE_SCOPE_CODE",
    "build_financial_change_view_invalidation_handler",
]
