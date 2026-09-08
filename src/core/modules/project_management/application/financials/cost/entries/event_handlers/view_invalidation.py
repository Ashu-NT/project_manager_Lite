from __future__ import annotations

from src.core.modules.project_management.application.financials.cost.entries.cost_entry_events import (
    CostEntryRecorded,
    CostEntryRemoved,
    CostEntryReversed,
    CostEntryStatusChangeType,
    CostEntryStatusChanged,
    CostEntryUpdated,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntryStatus,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

COST_ENTRY_CATEGORY = "cost_entry"
COST_ENTRY_LIST_SCOPE_CODE = "cost_entry_list"
COST_ENTRY_ACTUALS_SCOPE_CODE = "cost_entry_actuals"
COST_ENTRY_MODULE_CODE = "project_management"
COST_ENTRY_PROJECT_ENTITY_TYPE = "project"

_ProjectTarget = tuple[str, str, str, str, str, str]

_CostEntryEvent = (
    CostEntryRecorded
    | CostEntryUpdated
    | CostEntryStatusChanged
    | CostEntryReversed
    | CostEntryRemoved
)


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
        module_code=COST_ENTRY_MODULE_CODE,
        entity_type=COST_ENTRY_PROJECT_ENTITY_TYPE,
        entity_id=project_id,
    )


def _also_touches_actuals(event: _CostEntryEvent) -> bool:
    """Only POSTED/REVERSED entries count toward actual-cost aggregates (confirmed in source --
    `finance_snapshot_statements.py` filters `status.in_(("posted", "reversed"))`). Every other
    fact only ever changes what the cost-entry list/detail shows."""
    if isinstance(event, CostEntryRecorded):
        return event.status == ProjectCostEntryStatus.POSTED
    if isinstance(event, CostEntryStatusChanged):
        return event.change_type == CostEntryStatusChangeType.POSTED
    if isinstance(event, CostEntryReversed):
        return True
    return False


def build_cost_entry_view_invalidation_handler(channel: ViewInvalidationChannel):
    current_correlation_id: list[str | None] = [None]
    notified_targets: set[_ProjectTarget] = set()

    def handle_cost_entry_event(
        event: _CostEntryEvent,
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
        scope_codes = [COST_ENTRY_LIST_SCOPE_CODE]
        if _also_touches_actuals(event):
            scope_codes.append(COST_ENTRY_ACTUALS_SCOPE_CODE)

        for scope_code in scope_codes:
            target = _project_scope_target(scope_code, scope)
            if target in notified_targets:
                continue
            notified_targets.add(target)
            channel.notify(
                ViewInvalidationHint(
                    scope=scope,
                    category=COST_ENTRY_CATEGORY,
                    scope_code=scope_code,
                    entity_type=COST_ENTRY_PROJECT_ENTITY_TYPE,
                    entity_id=event.project_id,
                )
            )

    return handle_cost_entry_event


__all__ = [
    "build_cost_entry_view_invalidation_handler",
    "COST_ENTRY_CATEGORY",
    "COST_ENTRY_LIST_SCOPE_CODE",
    "COST_ENTRY_ACTUALS_SCOPE_CODE",
    "COST_ENTRY_MODULE_CODE",
    "COST_ENTRY_PROJECT_ENTITY_TYPE",
]
