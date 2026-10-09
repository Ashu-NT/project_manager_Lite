from __future__ import annotations

from src.core.modules.project_management.application.collaboration.collaboration_events import (
    TaskCommentChanged,
)
from src.core.modules.project_management.application.tasks.task_events import (
    TaskAssignmentChanged,
)
from src.core.platform.domain.approval.events import (
    ApprovalApproved,
    ApprovalRejected,
    ApprovalRequested,
)


def test_notification_subscriptions_share_one_dispatcher_without_duplicates(services) -> None:
    project_dispatcher = services["project_service"]._uow_factory._transactional_dispatcher
    task_dispatcher = services["task_service"]._task_uow_factory._transactional_dispatcher
    assert task_dispatcher is project_dispatcher

    for event_type, owner in (
        (ApprovalRequested, "register_platform_notification_policy"),
        (ApprovalApproved, "register_platform_notification_policy"),
        (ApprovalRejected, "register_platform_notification_policy"),
        (TaskAssignmentChanged, "register_pm_notification_policy"),
        (TaskCommentChanged, "register_pm_notification_policy"),
    ):
        handlers = project_dispatcher._handlers.get(event_type, ())
        assert sum(owner in handler.__qualname__ for handler in handlers) == 1
