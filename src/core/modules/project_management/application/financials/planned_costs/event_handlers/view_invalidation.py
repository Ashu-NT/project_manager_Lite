from __future__ import annotations

from src.core.modules.project_management.application.financials.planned_costs.planned_cost_events import (
    PlannedCostSnapshotCalculated,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

PLANNED_COST_CATEGORY = "planned_cost"
PLANNED_COST_SNAPSHOT_SCOPE_CODE = "planned_cost_snapshot"
PLANNED_COST_MODULE_CODE = "project_management"
PLANNED_COST_PROJECT_ENTITY_TYPE = "project"

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
        module_code=PLANNED_COST_MODULE_CODE,
        entity_type=PLANNED_COST_PROJECT_ENTITY_TYPE,
        entity_id=project_id,
    )


def build_planned_cost_view_invalidation_handler(channel: ViewInvalidationChannel):

    current_correlation_id: list[str | None] = [None]
    notified_targets: set[_ProjectTarget] = set()

    def handle_planned_cost_event(
        event: PlannedCostSnapshotCalculated,
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
        target = _project_scope_target(PLANNED_COST_SNAPSHOT_SCOPE_CODE, scope)
        if target in notified_targets:
            return
        notified_targets.add(target)
        channel.notify(
            ViewInvalidationHint(
                scope=scope,
                category=PLANNED_COST_CATEGORY,
                scope_code=PLANNED_COST_SNAPSHOT_SCOPE_CODE,
                entity_type=PLANNED_COST_PROJECT_ENTITY_TYPE,
                entity_id=event.project_id,
            )
        )

    return handle_planned_cost_event


__all__ = [
    "build_planned_cost_view_invalidation_handler",
    "PLANNED_COST_CATEGORY",
    "PLANNED_COST_SNAPSHOT_SCOPE_CODE",
    "PLANNED_COST_MODULE_CODE",
    "PLANNED_COST_PROJECT_ENTITY_TYPE",
]
