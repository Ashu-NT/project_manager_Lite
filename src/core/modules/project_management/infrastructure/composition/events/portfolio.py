from __future__ import annotations

from src.core.modules.project_management.application.portfolio.event_handlers.view_invalidation import (
    build_portfolio_view_invalidation_handler,
)
from src.core.modules.project_management.application.portfolio.portfolio_events import (
    PortfolioIntakeItemChanged,
    PortfolioProjectDependencyChanged,
    PortfolioScenarioChanged,
    PortfolioScoringTemplateChanged,
)
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)


def register_portfolio_view_invalidation(
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    handler = build_portfolio_view_invalidation_handler(view_channel)
    for event_type in (
        PortfolioIntakeItemChanged,
        PortfolioScenarioChanged,
        PortfolioScoringTemplateChanged,
        PortfolioProjectDependencyChanged,
    ):
        post_commit_bus.subscribe(event_type, handler)
