"""Notification policy registered at composition, outside Platform domain code."""

import json

from sqlalchemy import select

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

def register_pm_notification_policy(dispatcher) -> None:
    from src.core.modules.project_management.application.collaboration.collaboration_events import (
        TaskCommentChanged,
        TaskCommentChangeType,
    )
    from src.core.modules.project_management.application.tasks.task_events import (
        TaskAssignmentChanged,
        TaskAssignmentChangeType,
    )
    from src.core.modules.project_management.infrastructure.persistence.orm.collaboration import (
        TaskCommentORM,
    )
    from src.core.modules.project_management.infrastructure.persistence.orm.resource import (
        ResourceORM,
    )
    from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import (
        EmployeeORM,
    )
    from src.core.platform.infrastructure.persistence.orm.security.auth.auth import (
        UserORM,
    )
    from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.user_tenant import (
        UserTenantORM,
    )

    def assignment(event, uow) -> None:
        if event.change_type != TaskAssignmentChangeType.ASSIGNED:
            return
        recipient = uow._session.scalar(
            select(UserORM.id)
            .join(EmployeeORM, EmployeeORM.user_id == UserORM.id)
            .join(ResourceORM, ResourceORM.employee_id == EmployeeORM.id)
            .join(UserTenantORM, UserTenantORM.user_id == UserORM.id)
            .where(
                ResourceORM.id == event.resource_id,
                ResourceORM.tenant_id == event.tenant_id,
                ResourceORM.organization_id == event.organization_id,
                ResourceORM.is_active.is_(True),
                EmployeeORM.tenant_id == event.tenant_id,
                EmployeeORM.organization_id == event.organization_id,
                UserTenantORM.tenant_id == event.tenant_id,
                UserTenantORM.status == "active",
                UserTenantORM.revoked_at.is_(None),
                UserORM.is_active.is_(True),
            )
        )
        if recipient:
            enqueue_notification_work(
                uow._session, tenant_id=event.tenant_id,
                organization_id=event.organization_id,
                source_event_id=event.event_id, recipient_user_id=recipient,
                category="pm.task.assigned.v1", title="You were assigned a task",
                body="Open the task to view your assignment if you still have access.",
                metadata={"task_id": event.task_id, "project_id": event.project_id},
            )

    def mention(event, uow) -> None:
        if event.change_type != TaskCommentChangeType.CREATED:
            return
        comment = uow._session.get(TaskCommentORM, event.comment_id)
        if comment is None or comment.task_id != event.task_id or comment.deleted_at is not None:
            raise ValueError("Comment event has no live scoped comment")
        recipients = set(json.loads(comment.mentioned_user_ids_json))
        recipients.discard(comment.author_user_id)
        for user_id in sorted(recipients):
            eligible = uow._session.scalar(
                select(UserORM.id)
                .join(UserTenantORM, UserTenantORM.user_id == UserORM.id)
                .where(
                    UserORM.id == user_id, UserORM.is_active.is_(True),
                    UserTenantORM.tenant_id == event.tenant_id,
                    UserTenantORM.status == "active", UserTenantORM.revoked_at.is_(None),
                )
            )
            if eligible:
                enqueue_notification_work(
                    uow._session, tenant_id=event.tenant_id,
                    organization_id=event.organization_id,
                    source_event_id=event.event_id, recipient_user_id=eligible,
                    category="pm.comment.mentioned.v1",
                    title="You were mentioned in a comment",
                    body="Open the task discussion to view this mention if you still have access.",
                    metadata={"task_id": event.task_id, "project_id": event.project_id},
                )

    dispatcher.subscribe(TaskAssignmentChanged, assignment)
    dispatcher.subscribe(TaskCommentChanged, mention)
