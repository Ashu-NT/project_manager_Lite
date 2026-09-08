from __future__ import annotations

from src.core.modules.project_management.application.financials.budgets.budget_events import (
    BudgetLineChanged,
    BudgetProfileUpdated,
    BudgetRemoved,
    BudgetStatusChanged,
    BudgetVersionCreated,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

BUDGET_CATEGORY = "budget"
BUDGET_PLANNING_SCOPE_CODE = "budget_planning"
BUDGET_PROJECT_SUMMARY_SCOPE_CODE = "budget_project_summary"
BUDGET_MODULE_CODE = "project_management"
BUDGET_PROJECT_ENTITY_TYPE = "project"

_ProjectTarget = tuple[str, str, str, str, str, str]

_BudgetEvent = (
    BudgetVersionCreated
    | BudgetProfileUpdated
    | BudgetLineChanged
    | BudgetStatusChanged
    | BudgetRemoved
)

# Every current Budget fact stales both destinations -- the legacy `budgets_changed` signal never
# differentiated by fact type either (its one consumer in `financials_refresh_mixin.py` and its one
# consumer in `project_domain_event_binder.py` both reacted to every emission uniformly), so this
# uniform mapping is source-preserving, not an invented fan-out.
_SCOPE_CODES = (BUDGET_PLANNING_SCOPE_CODE, BUDGET_PROJECT_SUMMARY_SCOPE_CODE)


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
        module_code=BUDGET_MODULE_CODE,
        entity_type=BUDGET_PROJECT_ENTITY_TYPE,
        entity_id=project_id,
    )


def build_budget_view_invalidation_handler(channel: ViewInvalidationChannel):
    current_correlation_id: list[str | None] = [None]
    notified_targets: set[_ProjectTarget] = set()

    def handle_budget_event(
        event: _BudgetEvent,
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
                    category=BUDGET_CATEGORY,
                    scope_code=scope_code,
                    entity_type=BUDGET_PROJECT_ENTITY_TYPE,
                    entity_id=event.project_id,
                )
            )

    return handle_budget_event


__all__ = [
    "build_budget_view_invalidation_handler",
    "BUDGET_CATEGORY",
    "BUDGET_PLANNING_SCOPE_CODE",
    "BUDGET_PROJECT_SUMMARY_SCOPE_CODE",
    "BUDGET_MODULE_CODE",
    "BUDGET_PROJECT_ENTITY_TYPE",
]
