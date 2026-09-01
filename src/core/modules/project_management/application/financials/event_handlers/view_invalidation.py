from __future__ import annotations

from src.core.modules.project_management.application.financials.configuration_events import (
    ProjectFinancialProfileTransitioned,
    ProjectFinancialProfileUpdated,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

FINANCIAL_SETUP_CATEGORY = "financial_setup"
FINANCIAL_PROFILE_SCOPE_CODE = "financial_profile"
FINANCIAL_SETUP_MODULE_CODE = "project_management"
FINANCIAL_SETUP_PROJECT_ENTITY_TYPE = "project"

_ProjectTarget = tuple[str, str, str, str, str, str]


def _project_scope_target(scope_code: str, scope: ResourceScope) -> _ProjectTarget:
    """Dedupe identity is the (scope_code, target/scope) identity -- never a raw event field
    (P18B-FIX principle, applied from day one here)."""
    return (
        scope_code,
        scope.tenant_id,
        scope.organization_id,
        scope.module_code,
        scope.entity_type,
        scope.entity_id,
    )


def build_financial_profile_view_invalidation_handler(channel: ViewInvalidationChannel):

    current_correlation_id: list[str | None] = [None]
    notified_targets: set[_ProjectTarget] = set()

    def handle_financial_profile_event(
        event: ProjectFinancialProfileUpdated | ProjectFinancialProfileTransitioned,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_targets.clear()

        scope = ResourceScope(
            tenant_id=event.tenant_id,
            organization_id=event.organization_id,
            module_code=FINANCIAL_SETUP_MODULE_CODE,
            entity_type=FINANCIAL_SETUP_PROJECT_ENTITY_TYPE,
            entity_id=event.project_id,
        )
        target = _project_scope_target(FINANCIAL_PROFILE_SCOPE_CODE, scope)
        if target in notified_targets:
            return
        notified_targets.add(target)

        channel.notify(
            ViewInvalidationHint(
                scope=scope,
                category=FINANCIAL_SETUP_CATEGORY,
                scope_code=FINANCIAL_PROFILE_SCOPE_CODE,
                entity_type=FINANCIAL_SETUP_PROJECT_ENTITY_TYPE,
                entity_id=event.project_id,
            )
        )

    return handle_financial_profile_event


__all__ = [
    "build_financial_profile_view_invalidation_handler",
    "FINANCIAL_SETUP_CATEGORY",
    "FINANCIAL_PROFILE_SCOPE_CODE",
    "FINANCIAL_SETUP_MODULE_CODE",
    "FINANCIAL_SETUP_PROJECT_ENTITY_TYPE",
]
