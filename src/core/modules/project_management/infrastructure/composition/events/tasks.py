from __future__ import annotations

from src.core.modules.project_management.application.tasks.event_handlers.view_invalidation import (
    build_task_view_invalidation_handler,
)
from src.core.modules.project_management.application.tasks.task_events import (
    TaskAssignmentChanged,
    TaskCreated,
    TaskDependencyChanged,
    TaskHierarchyChanged,
    TaskProfileUpdated,
    TaskProgressChanged,
    TaskRemoved,
    TaskScheduleChanged,
    TaskStatusChanged,
)
from src.core.modules.project_management.infrastructure.composition.registrations.notifications import (
    register_pm_notification_policy,
)
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)


def register_task_events(
    transactional_dispatcher: InProcessTransactionalEventDispatcher,
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    register_pm_notification_policy(transactional_dispatcher)
    handler = build_task_view_invalidation_handler(view_channel)
    for event_type in (
        TaskCreated,
        TaskProfileUpdated,
        TaskHierarchyChanged,
        TaskStatusChanged,
        TaskProgressChanged,
        TaskScheduleChanged,
        TaskRemoved,
        TaskAssignmentChanged,
        TaskDependencyChanged,
    ):
        post_commit_bus.subscribe(event_type, handler)
