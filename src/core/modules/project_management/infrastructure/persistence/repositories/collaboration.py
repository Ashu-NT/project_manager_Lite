from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.modules.project_management.domain.identifiers import generate_id
from src.core.modules.project_management.contracts.repositories.collaboration import (
    TaskCommentRepository,
    TaskPresenceRepository,
)
from core.modules.project_management.domain.collaboration import TaskComment, TaskPresence
from src.core.modules.project_management.infrastructure.persistence.mappers.collaboration import (
    task_comment_from_orm,
    task_comment_to_orm,
    task_presence_from_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.collaboration import TaskCommentORM, TaskPresenceORM


class SqlAlchemyTaskCommentRepository(TaskCommentRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, comment: TaskComment) -> None:
        self.session.add(task_comment_to_orm(comment))

    def update(self, comment: TaskComment) -> None:
        self.session.merge(task_comment_to_orm(comment))

    def get(self, comment_id: str) -> Optional[TaskComment]:
        obj = self.session.get(TaskCommentORM, comment_id)
        return task_comment_from_orm(obj) if obj else None

    def list_by_task(self, task_id: str) -> List[TaskComment]:
        stmt = (
            select(TaskCommentORM)
            .where(TaskCommentORM.task_id == task_id)
            .order_by(TaskCommentORM.created_at.asc())
        )
        rows = self.session.execute(stmt).scalars().all()
        return [task_comment_from_orm(row) for row in rows]

    def list_recent_for_tasks(self, task_ids: List[str], limit: int = 200) -> List[TaskComment]:
        if not task_ids:
            return []
        stmt = (
            select(TaskCommentORM)
            .where(TaskCommentORM.task_id.in_(task_ids))
            .order_by(TaskCommentORM.created_at.desc())
            .limit(limit)
        )
        rows = self.session.execute(stmt).scalars().all()
        return [task_comment_from_orm(row) for row in rows]


class SqlAlchemyTaskPresenceRepository(TaskPresenceRepository):
    def __init__(self, session: Session):
        self.session = session

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
        stmt = select(TaskPresenceORM).where(
            TaskPresenceORM.task_id == task_id,
            TaskPresenceORM.username == normalized_username,
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
        )
        obj = self.session.execute(stmt).scalar_one_or_none()
        if obj is not None:
            self.session.delete(obj)

    def list_recent_for_tasks(
        self,
        task_ids: List[str],
        *,
        since,
        limit: int = 200,
    ) -> List[TaskPresence]:
        if not task_ids:
            return []
        stmt = (
            select(TaskPresenceORM)
            .where(
                TaskPresenceORM.task_id.in_(task_ids),
                TaskPresenceORM.last_seen_at >= since,
            )
            .order_by(TaskPresenceORM.last_seen_at.desc())
            .limit(limit)
        )
        rows = self.session.execute(stmt).scalars().all()
        return [task_presence_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyTaskCommentRepository", "SqlAlchemyTaskPresenceRepository"]
