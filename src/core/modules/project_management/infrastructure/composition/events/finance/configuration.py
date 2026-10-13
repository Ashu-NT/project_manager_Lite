from __future__ import annotations

from src.core.modules.project_management.application.financials.configuration.event_handlers.view_invalidation import (
    build_financial_profile_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.configuration.events import (
    CostCodeActivated,
    CostCodeCreated,
    CostCodeDeactivated,
    CostCodeProfileUpdated,
    ProjectCostCodeRestrictionAdded,
    ProjectCostCodeRestrictionRemoved,
    ProjectFinancialProfileCreated,
    ProjectFinancialProfileTransitioned,
    ProjectFinancialProfileUpdated,
)
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)


def register_financial_profile_view_invalidation(
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    handler = build_financial_profile_view_invalidation_handler(view_channel)
    for event_type in (
        ProjectFinancialProfileCreated,
        ProjectFinancialProfileUpdated,
        ProjectFinancialProfileTransitioned,
        CostCodeCreated,
        CostCodeProfileUpdated,
        CostCodeActivated,
        CostCodeDeactivated,
        ProjectCostCodeRestrictionAdded,
        ProjectCostCodeRestrictionRemoved,
    ):
        post_commit_bus.subscribe(event_type, handler)
