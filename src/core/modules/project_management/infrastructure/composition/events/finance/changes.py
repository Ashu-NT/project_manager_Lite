from __future__ import annotations

from src.core.modules.project_management.application.financials.financial_changes.event_handlers.view_invalidation import (
    build_financial_change_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.financial_changes.financial_change_events import (
    FinancialChangeChanged,
)
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)


def register_financial_change_view_invalidation(
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    post_commit_bus.subscribe(
        FinancialChangeChanged,
        build_financial_change_view_invalidation_handler(view_channel),
    )
