from __future__ import annotations

from src.core.modules.project_management.application.financials.invoicing.billing_events import (
    AccountingTransportFinalized,
    BillingPreparationCreated,
    BillingPreparationExternalOutcomeRecorded,
    BillingPreparationLineAdded,
    BillingPreparationLineRemoved,
    BillingPreparationStatusChanged,
    BillingProfileActivated,
    BillingProfileCreated,
    BillingScheduleLineAdded,
    BillingScheduleLineMarkedReady,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

BILLING_CATEGORY = "billing"
BILLING_COMMERCIAL_SCOPE_CODE = "billing_commercial"
BILLING_TRANSPORT_SCOPE_CODE = "billing_transport"
BILLING_MODULE_CODE = "project_management"
BILLING_PROJECT_ENTITY_TYPE = "project"

_ProjectTarget = tuple[str, str, str, str, str, str]

_BillingEvent = (
    BillingProfileCreated
    | BillingProfileActivated
    | BillingScheduleLineAdded
    | BillingScheduleLineMarkedReady
    | BillingPreparationCreated
    | BillingPreparationLineAdded
    | BillingPreparationLineRemoved
    | BillingPreparationStatusChanged
    | BillingPreparationExternalOutcomeRecorded
    | AccountingTransportFinalized
)

# Both aggregate families stale the same single real UI read area (Financials -> "commercial"),
# so every Billing fact maps to this one target -- distinct from the per-family typed DomainEvents,
# which describe what happened, not what became stale.
_SCOPE_CODES = (BILLING_COMMERCIAL_SCOPE_CODE,)


def _project_scope_target(scope_code: str, scope: ResourceScope) -> _ProjectTarget:
    return (
        scope_code,
        scope.tenant_id,
        scope.organization_id,
        scope.module_code,
        scope.entity_type,
        scope.entity_id,
    )


def _project_scope(*, tenant_id: str, organization_id: str, project_id: str) -> ResourceScope:
    return ResourceScope(
        tenant_id=tenant_id,
        organization_id=organization_id,
        module_code=BILLING_MODULE_CODE,
        entity_type=BILLING_PROJECT_ENTITY_TYPE,
        entity_id=project_id,
    )


def build_billing_view_invalidation_handler(channel: ViewInvalidationChannel):
    current_context: list[DomainEventContext | None] = [None]
    notified_targets: set[_ProjectTarget] = set()

    def handle_billing_event(
        event: _BillingEvent,
        context: DomainEventContext,
    ) -> None:
        if context is not current_context[0]:
            current_context[0] = context
            notified_targets.clear()

        scope = _project_scope(
            tenant_id=event.tenant_id,
            organization_id=event.organization_id,
            project_id=event.project_id,
        )
        scope_codes = (BILLING_TRANSPORT_SCOPE_CODE,) if isinstance(event, (AccountingTransportFinalized, BillingPreparationExternalOutcomeRecorded)) else _SCOPE_CODES
        for scope_code in scope_codes:
            target = _project_scope_target(scope_code, scope)
            if target in notified_targets:
                continue
            notified_targets.add(target)
            channel.notify(
                ViewInvalidationHint(
                    scope=scope,
                    category=BILLING_CATEGORY,
                    scope_code=scope_code,
                    entity_type=BILLING_PROJECT_ENTITY_TYPE,
                    entity_id=event.project_id,
                )
            )

    return handle_billing_event


__all__ = [
    "BILLING_CATEGORY",
    "BILLING_COMMERCIAL_SCOPE_CODE",
    "BILLING_MODULE_CODE",
    "BILLING_PROJECT_ENTITY_TYPE",
    "BILLING_TRANSPORT_SCOPE_CODE",
    "build_billing_view_invalidation_handler",
]
