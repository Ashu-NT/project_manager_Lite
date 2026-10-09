from __future__ import annotations

from src.core.modules.project_management.application.collaboration.collaboration_events import (
    TaskCommentChanged,
    TaskCommentReactionChanged,
    TaskCommentReadStateChanged,
)
from src.core.modules.project_management.application.collaboration.event_handlers.view_invalidation import (
    build_task_comment_view_invalidation_handler,
)
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)


def register_collaboration_view_invalidation(
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    handler = build_task_comment_view_invalidation_handler(view_channel)
    for event_type in (
        TaskCommentChanged,
        TaskCommentReactionChanged,
        TaskCommentReadStateChanged,
    ):
        post_commit_bus.subscribe(event_type, handler)
