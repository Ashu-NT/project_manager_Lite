from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.collaboration.collaboration import (
    TaskCommentRepository,
    TaskPresenceRepository,
)
from src.core.modules.project_management.domain.collaboration import TaskComment, TaskPresence
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM
from src.core.modules.project_management.infrastructure.persistence.mappers.collaboration import (
    task_comment_from_orm,
    task_comment_to_orm,
    task_presence_from_orm,
    task_presence_to_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.collaboration import TaskCommentORM, TaskPresenceORM
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds, TenantContextService
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyTaskCommentRepository(TaskCommentRepository):
    def __init__(self, session: Session):
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self) -> ActiveScopeIds:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "TaskCommentRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
            operation_label="access task comments"
        )

    def _project_scoped_stmt(self):
        ctx = self._context()
        return (
            select(TaskCommentORM)
            .join(TaskORM, TaskCommentORM.task_id == TaskORM.id)
            .join(ProjectORM, TaskORM.project_id == ProjectORM.id)
            .where(
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        )

    def _ensure_task_in_scope(self, task_id: str) -> None:
        ctx = self._context()
        task = self.session.execute(
            select(TaskORM.id)
            .join(ProjectORM, TaskORM.project_id == ProjectORM.id)
            .where(
                TaskORM.id == task_id,
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        ).scalar_one_or_none()
        if task is None:
            raise NotFoundError("Task not found.")

    def add(self, comment: TaskComment) -> None:
        self._ensure_task_in_scope(comment.task_id)
        self.session.add(task_comment_to_orm(comment))

    def update(self, comment: TaskComment) -> None:
        existing = self.get(comment.id)
        if existing is None:
            raise NotFoundError("Task comment not found.")
        self._ensure_task_in_scope(comment.task_id)
        mapped = task_comment_to_orm(comment)
        comment.version = update_with_version_check(
            self.session,
            TaskCommentORM,
            comment.id,
            comment.version,
            {
                "task_id": mapped.task_id,
                "author_user_id": mapped.author_user_id,
                "author_username": mapped.author_username,
                "body": mapped.body,
                "mentions_json": mapped.mentions_json,
                "mentioned_user_ids_json": mapped.mentioned_user_ids_json,
                "attachments_json": mapped.attachments_json,
                "read_by_json": mapped.read_by_json,
                "read_by_user_ids_json": mapped.read_by_user_ids_json,
                "created_at": mapped.created_at,
                "parent_comment_id": mapped.parent_comment_id,
                "updated_at": mapped.updated_at,
                "deleted_at": mapped.deleted_at,
                "deleted_by_user_id": mapped.deleted_by_user_id,
                "deletion_reason": mapped.deletion_reason,
                "reactions_json": mapped.reactions_json,
            },
            extra_filters={"task_id": comment.task_id},
            not_found_message="Task comment not found.",
            stale_message="This comment changed after it was loaded. Refresh the discussion and try again.",
        )

    def get(self, comment_id: str) -> TaskComment | None:
        stmt = self._project_scoped_stmt().where(TaskCommentORM.id == comment_id)
        row = self.session.execute(stmt).scalar_one_or_none()
        return task_comment_from_orm(row) if row else None

    def list_by_task(self, task_id: str) -> list[TaskComment]:
        stmt = (
            self._project_scoped_stmt()
            .where(TaskCommentORM.task_id == task_id)
            .order_by(TaskCommentORM.created_at.asc())
        )
        rows = self.session.execute(stmt).scalars().all()
        return [task_comment_from_orm(row) for row in rows]

    def list_recent_for_tasks(self, task_ids: list[str], limit: int = 200) -> list[TaskComment]:
        if not task_ids:
            return []
        ctx = self._context()
        stmt = (
            select(TaskCommentORM)
            .join(TaskORM, TaskCommentORM.task_id == TaskORM.id)
            .join(ProjectORM, TaskORM.project_id == ProjectORM.id)
            .where(
                TaskCommentORM.task_id.in_(task_ids),
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
            .order_by(TaskCommentORM.created_at.desc())
            .limit(limit)
        )
        rows = self.session.execute(stmt).scalars().all()
        return [task_comment_from_orm(row) for row in rows]


class SqlAlchemyTaskPresenceRepository(TaskPresenceRepository):
    def __init__(self, session: Session):
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self) -> ActiveScopeIds:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "TaskPresenceRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
            operation_label="access task presence"
        )

    def _scoped_task_ids(self):
        ctx = self._context()
        return (
            select(TaskORM.id)
            .join(ProjectORM, TaskORM.project_id == ProjectORM.id)
            .where(
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        )

    def _ensure_task_in_scope(self, task_id: str) -> None:
        task = self.session.execute(
            self._scoped_task_ids().where(TaskORM.id == task_id)
        ).scalar_one_or_none()
        if task is None:
            raise NotFoundError("Task not found.")

    def touch(
        self,
        *,
        task_id: str,
        user_id: str | None,
        username: str,
        display_name: str | None,
        activity: str,
    ) -> TaskPresence:
        candidate = TaskPresence.create(
            task_id=task_id,
            user_id=user_id,
            username=username,
            display_name=display_name,
            activity=activity,
        )
        self._ensure_task_in_scope(candidate.task_id)
        stmt = select(TaskPresenceORM).where(
            TaskPresenceORM.task_id == candidate.task_id,
            TaskPresenceORM.username == candidate.username,
            TaskPresenceORM.task_id.in_(self._scoped_task_ids()),
        )
        obj = self.session.execute(stmt).scalar_one_or_none()
        if obj is None:
            self.session.add(task_presence_to_orm(candidate))
            return candidate
        presence = TaskPresence(
            id=obj.id,
            task_id=obj.task_id,
            user_id=user_id,
            username=candidate.username,
            display_name=display_name,
            activity=activity,
            started_at=obj.started_at,
            last_seen_at=datetime.now(timezone.utc),
        )
        mapped = task_presence_to_orm(presence)
        obj.user_id = mapped.user_id
        obj.username = mapped.username
        obj.display_name = mapped.display_name
        obj.activity = mapped.activity
        obj.started_at = mapped.started_at
        obj.last_seen_at = mapped.last_seen_at
        return presence

    def clear(self, *, task_id: str, username: str) -> None:
        probe = TaskPresence.create(task_id=task_id, user_id=None, username=username)
        stmt = select(TaskPresenceORM).where(
            TaskPresenceORM.task_id == probe.task_id,
            TaskPresenceORM.username == probe.username,
            TaskPresenceORM.task_id.in_(self._scoped_task_ids()),
        )
        obj = self.session.execute(stmt).scalar_one_or_none()
        if obj is not None:
            self.session.delete(obj)

    def list_recent_for_tasks(
        self,
        task_ids: list[str],
        *,
        since,
        limit: int = 200,
    ) -> list[TaskPresence]:
        if not task_ids:
            return []
        stmt = (
            select(TaskPresenceORM)
            .where(
                TaskPresenceORM.task_id.in_(task_ids),
                TaskPresenceORM.task_id.in_(self._scoped_task_ids()),
                TaskPresenceORM.last_seen_at >= since,
            )
            .order_by(TaskPresenceORM.last_seen_at.desc())
            .limit(limit)
        )
        rows = self.session.execute(stmt).scalars().all()
        return [task_presence_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyTaskCommentRepository", "SqlAlchemyTaskPresenceRepository"]
