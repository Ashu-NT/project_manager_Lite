from __future__ import annotations

from src.core.modules.project_management.application.financials.commitments.commitment_events import (
    CommitmentLineChanged,
    CommitmentMatchChanged,
)
from src.core.modules.project_management.application.financials.commitments.event_handlers.view_invalidation import (
    build_commitment_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.cost.entries.cost_entry_events import (
    CostEntryRecorded,
    CostEntryRemoved,
    CostEntryReversed,
    CostEntryStatusChanged,
    CostEntryUpdated,
)
from src.core.modules.project_management.application.financials.cost.entries.event_handlers.view_invalidation import (
    build_cost_entry_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.planned_costs.event_handlers.view_invalidation import (
    build_planned_cost_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.planned_costs.planned_cost_events import (
    PlannedCostSnapshotCalculated,
)
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)


def register_planned_cost_view_invalidation(
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    post_commit_bus.subscribe(
        PlannedCostSnapshotCalculated,
        build_planned_cost_view_invalidation_handler(view_channel),
    )


def register_commitment_view_invalidation(
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    handler = build_commitment_view_invalidation_handler(view_channel)
    for event_type in (CommitmentLineChanged, CommitmentMatchChanged):
        post_commit_bus.subscribe(event_type, handler)


def register_cost_entry_view_invalidation(
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    handler = build_cost_entry_view_invalidation_handler(view_channel)
    for event_type in (
        CostEntryRecorded,
        CostEntryUpdated,
        CostEntryStatusChanged,
        CostEntryReversed,
        CostEntryRemoved,
    ):
        post_commit_bus.subscribe(event_type, handler)
