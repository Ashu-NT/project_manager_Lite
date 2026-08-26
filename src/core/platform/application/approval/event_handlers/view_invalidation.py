from __future__ import annotations

from src.core.platform.domain.approval.events import (
    ApprovalApproved,
    ApprovalRejected,
    ApprovalRequested,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

APPROVAL_CATEGORY = "approval"
APPROVAL_REQUESTS_SCOPE_CODE = "approval_requests"

_ApprovalEvent = ApprovalRequested | ApprovalApproved | ApprovalRejected


def build_approval_view_invalidation_handler(channel: ViewInvalidationChannel):
    """Returns one `PostCommitEventHandler` bound to `channel`, reused for explicit composition-
    root registration against all three Approval events (`post_commit_bus.subscribe(
    ApprovalRequested, handler)`, `subscribe(ApprovalApproved, handler)`,
    `subscribe(ApprovalRejected, handler)`)."""

    def handle_approval_event(event: _ApprovalEvent, context: DomainEventContext) -> None:
        channel.notify(
            ViewInvalidationHint(
                scope=OrganizationScope(event.tenant_id, event.organization_id),
                category=APPROVAL_CATEGORY,
                scope_code=APPROVAL_REQUESTS_SCOPE_CODE,
                entity_type="approval_request",
                entity_id=event.approval_id,
            )
        )

    return handle_approval_event


__all__ = [
    "build_approval_view_invalidation_handler",
    "APPROVAL_CATEGORY",
    "APPROVAL_REQUESTS_SCOPE_CODE",
]
