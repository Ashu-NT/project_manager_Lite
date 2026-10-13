from __future__ import annotations

from src.core.modules.project_management.application.risk.event_handlers.view_invalidation import (
    build_register_view_invalidation_handler,
)
from src.core.modules.project_management.application.risk.register_events import (
    RegisterEntryChanged,
)
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)


def register_register_view_invalidation(
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    post_commit_bus.subscribe(
        RegisterEntryChanged,
        build_register_view_invalidation_handler(view_channel),
    )
