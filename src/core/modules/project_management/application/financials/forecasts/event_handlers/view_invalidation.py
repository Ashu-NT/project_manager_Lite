from __future__ import annotations

from src.core.modules.project_management.application.financials.forecasts.forecast_events import (
    ForecastDraftGenerated,
    ForecastLineChanged,
    ForecastVersionChangeType,
    ForecastVersionChanged,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

FORECAST_CATEGORY = "forecast"
FORECAST_PLANNING_SCOPE_CODE = "forecast_planning"
FORECAST_APPROVED_BASIS_SCOPE_CODE = "forecast_approved_basis"
FORECAST_MODULE_CODE = "project_management"
FORECAST_PROJECT_ENTITY_TYPE = "project"

_ProjectTarget = tuple[str, str, str, str, str, str]


def _project_scope_target(scope_code: str, scope: ResourceScope) -> _ProjectTarget:
    """Dedupe identity is the (scope_code, target/scope) identity."""
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
        module_code=FORECAST_MODULE_CODE,
        entity_type=FORECAST_PROJECT_ENTITY_TYPE,
        entity_id=project_id,
    )


def build_forecast_view_invalidation_handler(channel: ViewInvalidationChannel):
    """One handler covering all three Forecast DomainEvent types, mirroring the read-model
    split proven from source (P19 §6): only `ForecastVersionChanged(APPROVED)` changes which
    forecast is the project's authoritative ETC basis -- CostPolicyEngine's
    `estimate_at_completion` and the performance/commercial projections it feeds only ever read
    the *approved* forecast (`facts.approved_forecast`), never a draft/submitted one. Every
    other Forecast fact (version create/submit/reject/delete, line add/update/remove, draft
    generation) can only ever touch a mutable, non-approved forecast
    (`_require_mutable_forecast` forbids editing an approved one), so it can only ever affect
    the forecast planning projection.

    Deduplicated per target, transaction-scoped (P18B-FIX): keyed by (transaction
    correlation_id, target identity), cleared the moment a new correlation_id arrives."""

    current_correlation_id: list[str | None] = [None]
    notified_targets: set[_ProjectTarget] = set()

    def _notify(scope_code: str, *, tenant_id: str, organization_id: str, project_id: str) -> None:
        scope = _project_scope(
            tenant_id=tenant_id, organization_id=organization_id, project_id=project_id
        )
        target = _project_scope_target(scope_code, scope)
        if target in notified_targets:
            return
        notified_targets.add(target)
        channel.notify(
            ViewInvalidationHint(
                scope=scope,
                category=FORECAST_CATEGORY,
                scope_code=scope_code,
                entity_type=FORECAST_PROJECT_ENTITY_TYPE,
                entity_id=project_id,
            )
        )

    def handle_forecast_event(
        event: ForecastVersionChanged | ForecastLineChanged | ForecastDraftGenerated,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_targets.clear()

        if (
            isinstance(event, ForecastVersionChanged)
            and event.change_type is ForecastVersionChangeType.APPROVED
        ):
            scope_code = FORECAST_APPROVED_BASIS_SCOPE_CODE
        else:
            scope_code = FORECAST_PLANNING_SCOPE_CODE

        _notify(
            scope_code,
            tenant_id=event.tenant_id,
            organization_id=event.organization_id,
            project_id=event.project_id,
        )

    return handle_forecast_event


__all__ = [
    "build_forecast_view_invalidation_handler",
    "FORECAST_CATEGORY",
    "FORECAST_PLANNING_SCOPE_CODE",
    "FORECAST_APPROVED_BASIS_SCOPE_CODE",
    "FORECAST_MODULE_CODE",
    "FORECAST_PROJECT_ENTITY_TYPE",
]
