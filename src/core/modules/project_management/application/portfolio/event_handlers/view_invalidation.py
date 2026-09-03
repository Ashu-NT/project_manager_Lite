from __future__ import annotations

from src.core.modules.project_management.application.portfolio.portfolio_events import (
    PortfolioIntakeItemChanged,
    PortfolioProjectDependencyChanged,
    PortfolioScenarioChanged,
    PortfolioScoringTemplateChanged,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

PORTFOLIO_CATEGORY = "portfolio"
PORTFOLIO_WORKSPACE_SCOPE_CODE = "portfolio_workspace"
PORTFOLIO_ENTITY_TYPE = "organization"

_PortfolioEvent = (
    PortfolioIntakeItemChanged
    | PortfolioScenarioChanged
    | PortfolioScoringTemplateChanged
    | PortfolioProjectDependencyChanged
)

_OrgTarget = tuple[str, str, str]


def _organization_scope_target(scope_code: str, scope: OrganizationScope) -> _OrgTarget:
    return (scope_code, scope.tenant_id, scope.organization_id)


def build_portfolio_view_invalidation_handler(channel: ViewInvalidationChannel):

    current_correlation_id: list[str | None] = [None]
    notified_targets: set[_OrgTarget] = set()

    def handle_portfolio_event(
        event: _PortfolioEvent,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_targets.clear()

        scope = OrganizationScope(event.tenant_id, event.organization_id)
        target = _organization_scope_target(PORTFOLIO_WORKSPACE_SCOPE_CODE, scope)
        if target in notified_targets:
            return
        notified_targets.add(target)
        channel.notify(
            ViewInvalidationHint(
                scope=scope,
                category=PORTFOLIO_CATEGORY,
                scope_code=PORTFOLIO_WORKSPACE_SCOPE_CODE,
                entity_type=PORTFOLIO_ENTITY_TYPE,
                entity_id=event.organization_id,
            )
        )

    return handle_portfolio_event


__all__ = [
    "build_portfolio_view_invalidation_handler",
    "PORTFOLIO_CATEGORY",
    "PORTFOLIO_WORKSPACE_SCOPE_CODE",
    "PORTFOLIO_ENTITY_TYPE",
]
