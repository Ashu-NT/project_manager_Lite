"""Platform Approval notification work is staged in its owning transaction."""

from src.core.platform.domain.approval.events import (
    ApprovalApproved,
    ApprovalRejected,
    ApprovalRequested,
)
from src.core.platform.infrastructure.persistence.repositories.notifications.notification_work import (
    enqueue_notification_work,
)


def register_platform_notification_policy(dispatcher) -> None:
    def approval(event, uow) -> None:
        request = uow.approvals.get(event.approval_id)
        if request is None:
            raise ValueError("Approval event has no scoped request")
        requested = isinstance(event, ApprovalRequested)
        category = "approval.requested.v1" if requested else (
            "approval.approved.v1" if isinstance(event, ApprovalApproved) else "approval.rejected.v1"
        )
        title = "Approval requested" if requested else (
            "Your approval request was approved" if isinstance(event, ApprovalApproved)
            else "Your approval request was rejected"
        )
        entity_label = request.entity_type.replace("_", " ")
        body = (
            f"{request.requested_by_username or 'Someone'} requested approval for a {entity_label}."
            if requested else f"Your {entity_label} request was {'approved' if isinstance(event, ApprovalApproved) else 'rejected'}."
        )
        audience = "reviewers" if requested else "requester"
        after = ""
        seen: set[str] = set()
        while True:
            recipients = uow.approvals.list_notification_recipient_ids(
                request.id, audience=audience, after_user_id=after, limit=100,
            )
            for user_id in recipients:
                if user_id in seen:
                    continue
                seen.add(user_id)
                enqueue_notification_work(
                    uow._session, tenant_id=event.tenant_id,
                    organization_id=event.organization_id,
                    source_event_id=event.event_id, recipient_user_id=user_id,
                    category=category, title=title, body=body,
                    metadata={"request_id": request.id, "request_type": request.request_type},
                )
            if len(recipients) < 100:
                break
            after = recipients[-1]

    for event_type in (ApprovalRequested, ApprovalApproved, ApprovalRejected):
        dispatcher.subscribe(event_type, approval)


__all__ = ["register_platform_notification_policy"]
