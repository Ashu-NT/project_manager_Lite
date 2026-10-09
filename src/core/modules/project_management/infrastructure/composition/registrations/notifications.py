"""PM notification handlers and delivery-time recipient eligibility."""

import json

from sqlalchemy import select

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
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.resource import (
    ResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskORM,
)
from src.core.platform.infrastructure.persistence.common.scoped_permission import (
    scoped_permission,
)
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import (
    EmployeeORM,
)
from src.core.platform.infrastructure.persistence.orm.security.auth.auth import UserORM
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.user_tenant import (
    UserTenantORM,
)
from src.core.platform.infrastructure.persistence.repositories.notifications.notification_work import (
    enqueue_notification_work,
)


def register_pm_notification_policy(dispatcher) -> None:
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
        if not recipients:
            return
        eligible_users = uow._session.scalars(
            select(UserORM.id)
            .join(UserTenantORM, UserTenantORM.user_id == UserORM.id)
            .where(
                UserORM.id.in_(recipients), UserORM.is_active.is_(True),
                UserTenantORM.tenant_id == event.tenant_id,
                UserTenantORM.status == "active", UserTenantORM.revoked_at.is_(None),
                scoped_permission(
                    user_id=UserORM.id, tenant_id=event.tenant_id,
                    organization_id=event.organization_id, project_id=event.project_id,
                    permissions=("collaboration.read",),
                ),
            )
        )
        for user_id in eligible_users:
            enqueue_notification_work(
                uow._session, tenant_id=event.tenant_id,
                organization_id=event.organization_id,
                source_event_id=event.event_id, recipient_user_id=user_id,
                category="pm.comment.mentioned.v1",
                title="You were mentioned in a comment",
                body="Open the task discussion to view this mention if you still have access.",
                metadata={
                    "task_id": event.task_id,
                    "project_id": event.project_id,
                    "comment_id": event.comment_id,
                },
            )

    dispatcher.subscribe(TaskAssignmentChanged, assignment)
    dispatcher.subscribe(TaskCommentChanged, mention)


def pm_notification_recipient_policy(session, work) -> bool:
    if work.category != "pm.comment.mentioned.v1":
        return True
    try:
        metadata = json.loads(work.metadata_json)
        comment_id = metadata["comment_id"]
        task_id = metadata["task_id"]
        project_id = metadata["project_id"]
    except (KeyError, TypeError, ValueError):
        return False
    comment = session.scalar(
        select(TaskCommentORM)
        .join(TaskORM, TaskORM.id == TaskCommentORM.task_id)
        .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
        .where(
            TaskCommentORM.id == comment_id,
            TaskCommentORM.task_id == task_id,
            TaskCommentORM.deleted_at.is_(None),
            TaskORM.project_id == project_id,
            ProjectORM.tenant_id == work.tenant_id,
            ProjectORM.organization_id == work.organization_id,
            scoped_permission(
                user_id=work.recipient_user_id,
                tenant_id=work.tenant_id,
                organization_id=work.organization_id,
                project_id=project_id,
                permissions=("collaboration.read",),
            ),
        )
    )
    if comment is None:
        return False
    try:
        return work.recipient_user_id in json.loads(comment.mentioned_user_ids_json)
    except (TypeError, ValueError):
        return False


__all__ = ["pm_notification_recipient_policy", "register_pm_notification_policy"]
