from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.platform.common.interfaces import TaskCommentRepository
from core.platform.common.models import TaskComment
from infra.modules.project_management.db.collaboration.mapper import task_comment_from_orm, task_comment_to_orm
from infra.platform.db.models import TaskCommentORM


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


__all__ = ["SqlAlchemyTaskCommentRepository"]
