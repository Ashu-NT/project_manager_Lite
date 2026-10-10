from __future__ import annotations

from src.core.modules.project_management.application.scheduling.baselines.baseline_events import (
    ProjectBaselineApproved,
    ProjectBaselineCreated,
    ProjectBaselineDeleted,
    ProjectBaselineRejected,
    ProjectBaselineSubmitted,
)
from src.core.modules.project_management.application.scheduling.baselines.event_handlers.view_invalidation import (
    build_baseline_view_invalidation_handler,
)
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)


def register_baseline_view_invalidation(
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    handler = build_baseline_view_invalidation_handler(view_channel)
    for event_type in (
        ProjectBaselineCreated,
        ProjectBaselineSubmitted,
        ProjectBaselineApproved,
        ProjectBaselineRejected,
        ProjectBaselineDeleted,
    ):
        post_commit_bus.subscribe(event_type, handler)
