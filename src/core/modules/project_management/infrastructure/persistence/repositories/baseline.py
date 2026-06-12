from __future__ import annotations


from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.baseline import BaselineRepository
from src.core.modules.project_management.domain.scheduling.baseline import (
    BaselineStatus,
    BaselineTask,
    BaselineVarianceRecord,
    ProjectBaseline,
)
from src.core.modules.project_management.infrastructure.persistence.mappers.baseline import (
    baseline_from_orm,
    baseline_task_from_orm,
    baseline_task_to_orm,
    baseline_to_orm,
    variance_record_from_orm,
    variance_record_to_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.baseline import (
    BaselineTaskORM,
    BaselineVarianceRecordORM,
    ProjectBaselineORM,
)


class SqlAlchemyBaselineRepository(BaselineRepository):
    def __init__(self, session: Session):
        self.session = session

    def add_baseline(self, baseline: ProjectBaseline) -> ProjectBaseline:
        self.session.add(baseline_to_orm(baseline))
        return baseline

    def update_baseline(self, baseline: ProjectBaseline) -> None:
        row = self.session.get(ProjectBaselineORM, baseline.id)
        if row is None:
            self.session.add(baseline_to_orm(baseline))
            return

        row.project_id = baseline.project_id
        row.name = baseline.name
        row.created_at = baseline.created_at
        row.status = baseline.status.value
        row.version = baseline.version
        row.submitted_by = baseline.submitted_by
        row.submitted_at = baseline.submitted_at
        row.approved_by = baseline.approved_by
        row.approved_at = baseline.approved_at
        row.notes = baseline.notes or None

    def get_baseline(self, baseline_id: str) -> ProjectBaseline | None:
        row = self.session.get(ProjectBaselineORM, baseline_id)
        return baseline_from_orm(row) if row else None

    def get_latest_for_project(self, project_id: str) -> ProjectBaseline | None:
        stmt = (
            select(ProjectBaselineORM)
            .where(ProjectBaselineORM.project_id == project_id)
            .order_by(ProjectBaselineORM.created_at.desc())
        )
        row = self.session.execute(stmt).scalars().first()
        return baseline_from_orm(row) if row else None

    def get_approved_baseline(self, project_id: str) -> ProjectBaseline | None:
        stmt = (
            select(ProjectBaselineORM)
            .where(ProjectBaselineORM.project_id == project_id)
            .where(ProjectBaselineORM.status == BaselineStatus.APPROVED.value)
            .order_by(ProjectBaselineORM.approved_at.desc(), ProjectBaselineORM.created_at.desc())
        )
        row = self.session.execute(stmt).scalars().first()
        return baseline_from_orm(row) if row else None

    def list_for_project(self, project_id: str) -> list[ProjectBaseline]:
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

    def add_baseline_tasks(self, tasks: list[BaselineTask]) -> None:
        self.session.add_all([baseline_task_to_orm(task) for task in tasks])

    def list_tasks(self, baseline_id: str) -> list[BaselineTask]:
        stmt = select(BaselineTaskORM).where(BaselineTaskORM.baseline_id == baseline_id)
        rows = self.session.execute(stmt).scalars().all()
        return [baseline_task_from_orm(row) for row in rows]

    def delete_tasks(self, baseline_id: str) -> None:
        stmt = delete(BaselineTaskORM).where(BaselineTaskORM.baseline_id == baseline_id)
        self.session.execute(stmt)

    def add_variance_records(self, records: list[BaselineVarianceRecord]) -> None:
        self.session.add_all([variance_record_to_orm(record) for record in records])

    def list_variance_records(self, new_baseline_id: str) -> list[BaselineVarianceRecord]:
        stmt = (
            select(BaselineVarianceRecordORM)
            .where(BaselineVarianceRecordORM.new_baseline_id == new_baseline_id)
            .order_by(
                BaselineVarianceRecordORM.created_at.desc(),
                BaselineVarianceRecordORM.task_name.asc(),
            )
        )
        rows = self.session.execute(stmt).scalars().all()
        return [variance_record_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyBaselineRepository"]
