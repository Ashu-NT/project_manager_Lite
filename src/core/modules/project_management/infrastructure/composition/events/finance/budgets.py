from __future__ import annotations

from src.core.modules.project_management.application.financials.budgets.budget_events import (
    BudgetLineChanged,
    BudgetProfileUpdated,
    BudgetRemoved,
    BudgetStatusChanged,
    BudgetVersionCreated,
)
from src.core.modules.project_management.application.financials.budgets.event_handlers.view_invalidation import (
    build_budget_view_invalidation_handler,
)
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)


def register_budget_view_invalidation(
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    handler = build_budget_view_invalidation_handler(view_channel)
    for event_type in (
        BudgetVersionCreated,
        BudgetProfileUpdated,
        BudgetLineChanged,
        BudgetStatusChanged,
        BudgetRemoved,
    ):
        post_commit_bus.subscribe(event_type, handler)
