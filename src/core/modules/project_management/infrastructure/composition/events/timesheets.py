from __future__ import annotations

from src.core.platform.application.time_management.time.event_handlers.view_invalidation import (
    build_timesheet_view_invalidation_handler,
)
from src.core.platform.application.time_management.time.timesheet_events import (
    TimesheetPeriodStatusChanged,
)
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)


def register_timesheet_view_invalidation(
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    post_commit_bus.subscribe(
        TimesheetPeriodStatusChanged,
        build_timesheet_view_invalidation_handler(view_channel),
    )
