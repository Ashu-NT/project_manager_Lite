from __future__ import annotations

from typing import List, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from core.interfaces import BaselineRepository
from core.models import BaselineTask, ProjectBaseline
from infra.db.baseline.mapper import (
    baseline_from_orm,
    baseline_task_from_orm,
    baseline_task_to_orm,
    baseline_to_orm,
)
from infra.db.models import BaselineTaskORM, ProjectBaselineORM


class SqlAlchemyBaselineRepository(BaselineRepository):
    def __init__(self, session: Session):
        self.session = session

    def add_baseline(self, baseline: ProjectBaseline) -> ProjectBaseline:
        self.session.add(baseline_to_orm(baseline))
        return baseline

    def get_baseline(self, baseline_id: str) -> Optional[ProjectBaseline]:
        row = self.session.get(ProjectBaselineORM, baseline_id)
        return baseline_from_orm(row) if row else None

    def get_latest_for_project(self, project_id: str) -> Optional[ProjectBaseline]:
        stmt = (
            select(ProjectBaselineORM)
            .where(ProjectBaselineORM.project_id == project_id)
            .order_by(ProjectBaselineORM.created_at.desc())
        )
        row = self.session.execute(stmt).scalars().first()
        return baseline_from_orm(row) if row else None

    def list_for_project(self, project_id: str) -> List[ProjectBaseline]:
        stmt = (
            select(ProjectBaselineORM)
            .where(ProjectBaselineORM.project_id == project_id)
            .order_by(ProjectBaselineORM.created_at.desc())
        )
        rows = self.session.execute(stmt).scalars().all()
        return [baseline_from_orm(row) for row in rows]

    def delete_baseline(self, baseline_id: str) -> None:
        row = self.session.get(ProjectBaselineORM, baseline_id)
        if row:
            self.session.delete(row)

    def add_baseline_tasks(self, tasks: List[BaselineTask]) -> None:
        self.session.add_all([baseline_task_to_orm(task) for task in tasks])

    def list_tasks(self, baseline_id: str) -> List[BaselineTask]:
        stmt = select(BaselineTaskORM).where(BaselineTaskORM.baseline_id == baseline_id)
        rows = self.session.execute(stmt).scalars().all()
        return [baseline_task_from_orm(row) for row in rows]

    def delete_tasks(self, baseline_id: str) -> None:
        stmt = delete(BaselineTaskORM).where(BaselineTaskORM.baseline_id == baseline_id)
        self.session.execute(stmt)


__all__ = ["SqlAlchemyBaselineRepository"]
