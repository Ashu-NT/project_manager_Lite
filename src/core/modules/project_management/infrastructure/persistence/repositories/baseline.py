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
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
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
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.tenancy.tenant_context import TenantContext, TenantContextService
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyBaselineRepository(BaselineRepository):
    def __init__(self, session: Session):
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "BaselineRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label="access baselines"
        )

    def _project_scoped_stmt(self):
        ctx = self._context()
        return (
            select(ProjectBaselineORM)
            .join(ProjectORM, ProjectBaselineORM.project_id == ProjectORM.id)
            .where(
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        )

    def _scoped_project_ids(self, *, project_id: str | None = None):
        ctx = self._context()
        stmt = select(ProjectORM.id).where(
            ProjectORM.tenant_id == ctx.tenant_id,
            ProjectORM.organization_id == ctx.organization_id,
        )
        if project_id is not None:
            stmt = stmt.where(ProjectORM.id == project_id)
        return stmt

    def _scoped_baseline_ids(self, *, baseline_id: str | None = None, project_id: str | None = None):
        stmt = select(ProjectBaselineORM.id).where(
            ProjectBaselineORM.project_id.in_(self._scoped_project_ids(project_id=project_id))
        )
        if baseline_id is not None:
            stmt = stmt.where(ProjectBaselineORM.id == baseline_id)
        return stmt

    def _ensure_project_in_scope(self, project_id: str) -> None:
        project = self.session.execute(
            self._scoped_project_ids(project_id=project_id)
        ).scalar_one_or_none()
        if project is None:
            raise NotFoundError("Project not found.")

    def _ensure_baselines_in_scope(self, baseline_ids: set[str]) -> None:
        if not baseline_ids:
            return
        rows = set(
            self.session.execute(
                select(ProjectBaselineORM.id).where(
                    ProjectBaselineORM.id.in_(baseline_ids),
                    ProjectBaselineORM.project_id.in_(self._scoped_project_ids()),
                )
            ).scalars().all()
        )
        if rows != baseline_ids:
            raise NotFoundError("Baseline not found.")

    def add_baseline(self, baseline: ProjectBaseline) -> ProjectBaseline:
        self._ensure_project_in_scope(baseline.project_id)
        self.session.add(baseline_to_orm(baseline))
        return baseline

    def update_baseline(self, baseline: ProjectBaseline) -> None:
        if self.get_baseline(baseline.id) is None:
            raise NotFoundError("Baseline not found.")
        self._ensure_project_in_scope(baseline.project_id)
        baseline.version = update_with_version_check(
            self.session,
            ProjectBaselineORM,
            baseline.id,
            getattr(baseline, "version", 1),
            {
                "project_id": baseline.project_id,
                "name": baseline.name,
                "created_at": baseline.created_at,
                "status": baseline.status.value,
                "submitted_by": baseline.submitted_by,
                "submitted_at": baseline.submitted_at,
                "approved_by": baseline.approved_by,
                "approved_at": baseline.approved_at,
                "notes": baseline.notes or None,
            },
            extra_filters={"project_id": baseline.project_id},
            not_found_message="Baseline not found.",
            stale_message="Baseline was updated by another user.",
        )

    def get_baseline(self, baseline_id: str) -> ProjectBaseline | None:
        stmt = self._project_scoped_stmt().where(ProjectBaselineORM.id == baseline_id)
        row = self.session.execute(stmt).scalar_one_or_none()
        return baseline_from_orm(row) if row else None

    def get_latest_for_project(self, project_id: str) -> ProjectBaseline | None:
        stmt = (
            self._project_scoped_stmt()
            .where(ProjectBaselineORM.project_id == project_id)
            .order_by(ProjectBaselineORM.created_at.desc())
        )
        row = self.session.execute(stmt).scalars().first()
        return baseline_from_orm(row) if row else None

    def get_approved_baseline(self, project_id: str) -> ProjectBaseline | None:
        stmt = (
            self._project_scoped_stmt()
            .where(ProjectBaselineORM.project_id == project_id)
            .where(ProjectBaselineORM.status == BaselineStatus.APPROVED.value)
            .order_by(ProjectBaselineORM.approved_at.desc(), ProjectBaselineORM.created_at.desc())
        )
        row = self.session.execute(stmt).scalars().first()
        return baseline_from_orm(row) if row else None

    def list_for_project(self, project_id: str) -> list[ProjectBaseline]:
        stmt = (
            self._project_scoped_stmt()
            .where(ProjectBaselineORM.project_id == project_id)
            .order_by(ProjectBaselineORM.created_at.desc())
        )
        rows = self.session.execute(stmt).scalars().all()
        return [baseline_from_orm(row) for row in rows]

    def delete_baseline(self, baseline_id: str) -> None:
        stmt = delete(ProjectBaselineORM).where(
            ProjectBaselineORM.id.in_(
                self._scoped_baseline_ids(baseline_id=baseline_id)
            )
        )
        self.session.execute(stmt)

    def add_baseline_tasks(self, tasks: list[BaselineTask]) -> None:
        self._ensure_baselines_in_scope({task.baseline_id for task in tasks})
        self.session.add_all([baseline_task_to_orm(task) for task in tasks])

    def list_tasks(self, baseline_id: str) -> list[BaselineTask]:
        stmt = select(BaselineTaskORM).where(
            BaselineTaskORM.baseline_id == baseline_id,
            BaselineTaskORM.baseline_id.in_(self._scoped_baseline_ids()),
        )
        rows = self.session.execute(stmt).scalars().all()
        return [baseline_task_from_orm(row) for row in rows]

    def delete_tasks(self, baseline_id: str) -> None:
        stmt = delete(BaselineTaskORM).where(
            BaselineTaskORM.baseline_id == baseline_id,
            BaselineTaskORM.baseline_id.in_(self._scoped_baseline_ids()),
        )
        self.session.execute(stmt)

    def add_variance_records(self, records: list[BaselineVarianceRecord]) -> None:
        self._ensure_baselines_in_scope({record.new_baseline_id for record in records})
        self.session.add_all([variance_record_to_orm(record) for record in records])

    def list_variance_records(self, new_baseline_id: str) -> list[BaselineVarianceRecord]:
        stmt = (
            select(BaselineVarianceRecordORM)
            .where(
                BaselineVarianceRecordORM.new_baseline_id == new_baseline_id,
                BaselineVarianceRecordORM.new_baseline_id.in_(self._scoped_baseline_ids()),
            )
            .order_by(
                BaselineVarianceRecordORM.created_at.desc(),
                BaselineVarianceRecordORM.task_name.asc(),
            )
        )
        rows = self.session.execute(stmt).scalars().all()
        return [variance_record_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyBaselineRepository"]
