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

    def _ensure_task_in_scope(self, task_id: str | None) -> None:
        if not task_id:
            return
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

    def add(self, cost_item: CostItem) -> None:
        self._ensure_project_in_scope(cost_item.project_id)
        self._ensure_task_in_scope(cost_item.task_id)
        self.session.add(cost_to_orm(cost_item))

    def update(self, cost_item: CostItem) -> None:
        if self.get(cost_item.id) is None:
            raise BusinessRuleError("Cost item not found.")
        self._ensure_project_in_scope(cost_item.project_id)
        self._ensure_task_in_scope(cost_item.task_id)
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

    def _require_project_id(self, project_id: str | None) -> str:
        normalized = str(project_id or "").strip()
        if not normalized:
            raise BusinessRuleError("Calendar event must belong to a project.")
        return normalized

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

    def _ensure_task_in_scope(self, task_id: str | None) -> None:
        if not task_id:
            return
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

    def add(self, event: CalendarEvent) -> None:
        project_id = self._require_project_id(event.project_id)
        self._ensure_project_in_scope(project_id)
        self._ensure_task_in_scope(event.task_id)
        self.session.add(event_to_orm(event))

    def update(self, event: CalendarEvent) -> None:
        row = (
            self.session.execute(
                self._project_scoped_stmt().where(CalendarEventORM.id == event.id)
            ).scalar_one_or_none()
        )
        if row is None:
            raise NotFoundError("Calendar event not found.")
        project_id = self._require_project_id(event.project_id)
        self._ensure_project_in_scope(project_id)
        self._ensure_task_in_scope(event.task_id)
        row.title = event.title
        row.start_date = event.start_date
        row.end_date = event.end_date
        row.project_id = project_id
        row.task_id = event.task_id
        row.all_day = event.all_day
        row.description = event.description

    def delete(self, event_id: str) -> None:
        self.session.execute(
            CalendarEventORM.__table__.delete().where(
                CalendarEventORM.id.in_(
                    self._project_scoped_stmt()
                    .where(CalendarEventORM.id == event_id)
                    .with_only_columns(CalendarEventORM.id)
                )
            )
        )

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
        self.session.execute(
            CalendarEventORM.__table__.delete().where(
                CalendarEventORM.id.in_(
                    self._project_scoped_stmt()
                    .where(CalendarEventORM.task_id == task_id)
                    .with_only_columns(CalendarEventORM.id)
                )
            )
        )

    def delete_for_project(self, project_id: str) -> None:
        self.session.execute(
            CalendarEventORM.__table__.delete().where(
                CalendarEventORM.id.in_(
                    self._project_scoped_stmt()
                    .where(CalendarEventORM.project_id == project_id)
                    .with_only_columns(CalendarEventORM.id)
                )
            )
        )

__all__ = [
    "SqlAlchemyCostRepository",
    "SqlAlchemyCalendarEventRepository",
]
