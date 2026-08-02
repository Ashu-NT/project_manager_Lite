from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.cost import (
    CostRepository,
)
from src.core.modules.project_management.domain.financials.cost import CostItem
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.mappers.cost import (
    cost_from_orm,
    cost_to_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.cost import CostItemORM
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.tenancy.tenant_context import TenantContext, TenantContextService
from src.infra.persistence.db.optimistic import update_with_version_check
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM


class SqlAlchemyCostRepository(CostRepository):
    def __init__(self, session: Session):
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "CostRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label="access costs"
        )

    def _project_scoped_stmt(self):
        ctx = self._context()
        return (
            select(CostItemORM)
            .join(ProjectORM, CostItemORM.project_id == ProjectORM.id)
            .where(
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        )

    def _ensure_project_in_scope(self, project_id: str) -> None:
        ctx = self._context()
        project = self.session.execute(
            select(ProjectORM.id).where(
                ProjectORM.id == project_id,
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        ).scalar_one_or_none()
        if project is None:
            raise NotFoundError("Project not found.")

    def _ensure_task_in_scope(
        self,
        task_id: str | None,
        *,
        project_id: str,
    ) -> None:
        if not task_id:
            return
        ctx = self._context()
        task = self.session.execute(
            select(TaskORM.id)
            .join(ProjectORM, TaskORM.project_id == ProjectORM.id)
            .where(
                TaskORM.id == task_id,
                TaskORM.project_id == project_id,
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        ).scalar_one_or_none()
        if task is None:
            raise NotFoundError("Task not found.")

    def add(self, cost_item: CostItem) -> None:
        self._ensure_project_in_scope(cost_item.project_id)
        self._ensure_task_in_scope(
            cost_item.task_id,
            project_id=cost_item.project_id,
        )
        self.session.add(cost_to_orm(cost_item))

    def update(self, cost_item: CostItem) -> None:
        if self.get(cost_item.id) is None:
            raise BusinessRuleError("Cost item not found.")
        self._ensure_project_in_scope(cost_item.project_id)
        self._ensure_task_in_scope(
            cost_item.task_id,
            project_id=cost_item.project_id,
        )
        cost_item.version = update_with_version_check(
            self.session,
            CostItemORM,
            cost_item.id,
            getattr(cost_item, "version", 1),
            {
                "project_id": cost_item.project_id,
                "task_id": cost_item.task_id,
                "cost_code": getattr(cost_item, "code", "") or None,
                "description": cost_item.description,
                "cost_type": (
                    cost_item.cost_type.value
                    if hasattr(cost_item.cost_type, "value")
                    else cost_item.cost_type
                ),
                "currency_code": cost_item.currency_code,
                "planned_amount": cost_item.planned_amount,
                "committed_amount": cost_item.committed_amount,
                "actual_amount": cost_item.actual_amount,
                "forecast_amount": cost_item.forecast_amount,
                "commitment_status": (
                    cost_item.commitment_status.value
                    if hasattr(cost_item.commitment_status, "value")
                    else cost_item.commitment_status
                ),
                "vendor_reference": cost_item.vendor_reference,
                "incurred_date": cost_item.incurred_date,
            },
            extra_filters={"project_id": cost_item.project_id},
            not_found_message="Cost item not found.",
            stale_message="Cost item was updated by another user.",
        )

    def delete(self, cost_id: str) -> None:
        self.session.execute(
            CostItemORM.__table__.delete().where(
                CostItemORM.id.in_(
                    self._project_scoped_stmt().where(CostItemORM.id == cost_id).with_only_columns(CostItemORM.id)
                )
            )
        )

    def list_by_project(self, project_id: str) -> list[CostItem]:
        stmt = self._project_scoped_stmt().where(CostItemORM.project_id == project_id)
        rows = self.session.execute(stmt).scalars().all()
        return [cost_from_orm(row) for row in rows]

    def delete_by_project(self, project_id: str) -> None:
        self.session.execute(
            CostItemORM.__table__.delete().where(
                CostItemORM.id.in_(
                    self._project_scoped_stmt()
                    .where(CostItemORM.project_id == project_id)
                    .with_only_columns(CostItemORM.id)
                )
            )
        )

    def get(self, cost_id: str) -> CostItem | None:
        stmt = self._project_scoped_stmt().where(CostItemORM.id == cost_id)
        row = self.session.execute(stmt).scalar_one_or_none()
        return cost_from_orm(row) if row else None


__all__ = [
    "SqlAlchemyCostRepository",
]
