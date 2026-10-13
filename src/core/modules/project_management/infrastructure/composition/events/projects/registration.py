from __future__ import annotations

from src.core.modules.project_management.application.projects.event_handlers.view_invalidation import (
    build_project_view_invalidation_handler,
)
from src.core.modules.project_management.application.projects.project_events import (
    ProjectCreated,
    ProjectProfileUpdated,
    ProjectRemoved,
    ProjectStatusChanged,
)
from src.core.modules.project_management.application.resources.project_resources.project_resource_events import (
    ProjectResourceAssignmentChanged,
)
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)


def register_project_view_invalidation(
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    handler = build_project_view_invalidation_handler(view_channel)
    for event_type in (
        ProjectCreated,
        ProjectProfileUpdated,
        ProjectStatusChanged,
        ProjectRemoved,
        ProjectResourceAssignmentChanged,
    ):
        post_commit_bus.subscribe(event_type, handler)
