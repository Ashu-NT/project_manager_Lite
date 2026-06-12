from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.modules.project_management.contracts.repositories.collaboration import (
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
)
from src.core.modules.project_management.infrastructure.persistence.orm.collaboration import TaskCommentORM, TaskPresenceORM
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.tenancy.tenant_context import TenantContext, TenantContextService


class SqlAlchemyTaskCommentRepository(TaskCommentRepository):
    def __init__(self, session: Session):
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "TaskCommentRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
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
        row = (
            self.session.execute(
                self._project_scoped_stmt().where(TaskCommentORM.id == comment.id)
            ).scalar_one_or_none()
        )
        if row is None:
            raise NotFoundError("Task comment not found.")
        self._ensure_task_in_scope(comment.task_id)
        mapped = task_comment_to_orm(comment)
        row.task_id = mapped.task_id
        row.author_user_id = mapped.author_user_id
        row.author_username = mapped.author_username
        row.body = mapped.body
        row.mentions_json = mapped.mentions_json
        row.mentioned_user_ids_json = mapped.mentioned_user_ids_json
        row.attachments_json = mapped.attachments_json
        row.read_by_json = mapped.read_by_json
        row.read_by_user_ids_json = mapped.read_by_user_ids_json
        row.created_at = mapped.created_at

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

    def _context(self) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "TaskPresenceRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
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
        normalized_username = str(username or "").strip().lower()
        self._ensure_task_in_scope(task_id)
        stmt = select(TaskPresenceORM).where(
            TaskPresenceORM.task_id == task_id,
            TaskPresenceORM.username == normalized_username,
            TaskPresenceORM.task_id.in_(self._scoped_task_ids()),
        )
        obj = self.session.execute(stmt).scalar_one_or_none()
        now = datetime.now()
        if obj is None:
            obj = TaskPresenceORM(
                id=generate_id(),
                task_id=task_id,
                user_id=user_id,
                username=normalized_username,
                display_name=(display_name or "").strip() or None,
                activity=(activity or "reviewing").strip().lower(),
                started_at=now,
                last_seen_at=now,
            )
            self.session.add(obj)
        else:
            obj.user_id = user_id
            obj.display_name = (display_name or "").strip() or None
            obj.activity = (activity or "reviewing").strip().lower()
            obj.last_seen_at = now
        return task_presence_from_orm(obj)

    def clear(self, *, task_id: str, username: str) -> None:
        normalized_username = str(username or "").strip().lower()
        stmt = select(TaskPresenceORM).where(
            TaskPresenceORM.task_id == task_id,
            TaskPresenceORM.username == normalized_username,
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
