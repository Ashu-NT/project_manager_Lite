from __future__ import annotations

from src.core.modules.project_management.application.financials.invoicing.billing_events import (
    BillingPreparationCreated,
    BillingPreparationExternalOutcomeRecorded,
    BillingPreparationLineAdded,
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
    | BillingPreparationStatusChanged
    | BillingPreparationExternalOutcomeRecorded
)

# Both aggregate families stale the same single real UI read area (Financials -> "commercial") --
# P38A/P39 found no independent per-family cached projection, so every current Billing fact maps
# to this one target. DomainEvents describe what happened (kept per-family, distinct classes);
# ViewInvalidation describes what became stale (one shared target) -- these are deliberately not
# the same design axis.
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
    current_correlation_id: list[str | None] = [None]
    notified_targets: set[_ProjectTarget] = set()

    def handle_billing_event(
        event: _BillingEvent,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_targets.clear()

        scope = _project_scope(
            tenant_id=event.tenant_id,
            organization_id=event.organization_id,
            project_id=event.project_id,
        )
        for scope_code in _SCOPE_CODES:
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
    "build_billing_view_invalidation_handler",
    "BILLING_CATEGORY",
    "BILLING_COMMERCIAL_SCOPE_CODE",
    "BILLING_MODULE_CODE",
    "BILLING_PROJECT_ENTITY_TYPE",
]
