"""Platform Approval read-side invalidation subscriptions."""

from src.core.platform.application.approval.event_handlers.view_invalidation import (
    build_approval_view_invalidation_handler,
)
from src.core.platform.domain.approval.events import (
    ApprovalApproved,
    ApprovalRejected,
    ApprovalRequested,
)
from src.core.shared.events.domain_event_subscriber import PostCommitEventSubscriber
from src.core.shared.events.view_invalidation import ViewInvalidationChannel


def register_approval_views(
    bus: PostCommitEventSubscriber,
    channel: ViewInvalidationChannel,
) -> None:
    handler = build_approval_view_invalidation_handler(channel)
    for approval_event_type in (ApprovalRequested, ApprovalApproved, ApprovalRejected):
        bus.subscribe(approval_event_type, handler)


__all__ = ["register_approval_views"]
