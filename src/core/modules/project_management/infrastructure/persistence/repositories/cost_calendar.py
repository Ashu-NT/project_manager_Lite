from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.cost_calendar import (
    CalendarEventRepository,
    CostRepository,
)
from src.core.modules.project_management.domain.scheduling.calendar import CalendarEvent
from src.core.modules.project_management.domain.financials.cost import CostItem
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.mappers.cost_calendar import (
    cost_from_orm,
    cost_to_orm,
    event_from_orm,
    event_to_orm,
)
from src.core.modules.project_management.infrastructure.persistence.orm.cost_calendar import CalendarEventORM, CostItemORM
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.tenancy.tenant_context import TenantContext, TenantContextService
from src.infra.persistence.db.optimistic import update_with_version_check


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

    def add(self, cost_item: CostItem) -> None:
        self.session.add(cost_to_orm(cost_item))

    def update(self, cost_item: CostItem) -> None:
        if self.get(cost_item.id) is None:
            raise BusinessRuleError("Cost item not found.")
        cost_item.version = update_with_version_check(
            self.session,
            CostItemORM,
            cost_item.id,
            getattr(cost_item, "version", 1),
            {
                "project_id": cost_item.project_id,
                "task_id": cost_item.task_id,
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
                "incurred_date": cost_item.incurred_date,
            },
            not_found_message="Cost item not found.",
            stale_message="Cost item was updated by another user.",
        )

    def delete(self, cost_id: str) -> None:
        self.session.query(CostItemORM).filter_by(id=cost_id).delete()

    def list_by_project(self, project_id: str) -> list[CostItem]:
        stmt = self._project_scoped_stmt().where(CostItemORM.project_id == project_id)
        rows = self.session.execute(stmt).scalars().all()
        return [cost_from_orm(row) for row in rows]

    def delete_by_project(self, project_id: str) -> None:
        self.session.query(CostItemORM).filter_by(project_id=project_id).delete()

    def get(self, cost_id: str) -> CostItem | None:
        stmt = self._project_scoped_stmt().where(CostItemORM.id == cost_id)
        row = self.session.execute(stmt).scalar_one_or_none()
        return cost_from_orm(row) if row else None


class SqlAlchemyCalendarEventRepository(CalendarEventRepository):
    def __init__(self, session: Session):
        self.session = session
        self._tenant_context_service: TenantContextService | None = None

    def _context(self) -> TenantContext:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "CalendarEventRepository requires TenantContextService.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_organization_context(
            operation_label="access calendar events"
        )

    def _project_scoped_stmt(self):
        ctx = self._context()
        return (
            select(CalendarEventORM)
            .join(ProjectORM, CalendarEventORM.project_id == ProjectORM.id)
            .where(
                CalendarEventORM.project_id.isnot(None),
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        )

    def add(self, event: CalendarEvent) -> None:
        self.session.add(event_to_orm(event))

    def update(self, event: CalendarEvent) -> None:
        self.session.merge(event_to_orm(event))

    def delete(self, event_id: str) -> None:
        self.session.query(CalendarEventORM).filter_by(id=event_id).delete()

    def get(self, event_id: str) -> CalendarEvent | None:
        stmt = self._project_scoped_stmt().where(CalendarEventORM.id == event_id)
        row = self.session.execute(stmt).scalar_one_or_none()
        return event_from_orm(row) if row else None

    def list_for_project(self, project_id: str) -> list[CalendarEvent]:
        stmt = self._project_scoped_stmt().where(CalendarEventORM.project_id == project_id)
        rows = self.session.execute(stmt).scalars().all()
        return [event_from_orm(row) for row in rows]

    def list_range(self, start_date: date, end_date: date) -> list[CalendarEvent]:
        ctx = self._context()
        stmt = (
            select(CalendarEventORM)
            .join(ProjectORM, CalendarEventORM.project_id == ProjectORM.id)
            .where(
                CalendarEventORM.project_id.isnot(None),
                CalendarEventORM.end_date >= start_date,
                CalendarEventORM.start_date <= end_date,
                ProjectORM.tenant_id == ctx.tenant_id,
                ProjectORM.organization_id == ctx.organization_id,
            )
        )
        rows = self.session.execute(stmt).scalars().all()
        return [event_from_orm(row) for row in rows]

    def delete_for_task(self, task_id: str) -> None:
        self.session.query(CalendarEventORM).filter_by(task_id=task_id).delete()

    def delete_for_project(self, project_id: str) -> None:
        self.session.query(CalendarEventORM).filter_by(project_id=project_id).delete()

__all__ = [
    "SqlAlchemyCostRepository",
    "SqlAlchemyCalendarEventRepository",
]
