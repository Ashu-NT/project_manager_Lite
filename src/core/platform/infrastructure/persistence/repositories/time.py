from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.time.contracts import TimeEntryRepository, TimesheetPeriodRepository
from src.core.platform.time.domain import TimeEntry, TimesheetPeriod, TimesheetPeriodStatus
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantScopedRepositorySupport,
)
from src.core.platform.infrastructure.persistence.orm.time import TimeEntryORM, TimesheetPeriodORM
from src.core.platform.infrastructure.persistence.mappers.time import (
    time_entry_from_orm,
    time_entry_to_orm,
    timesheet_period_from_orm,
    timesheet_period_to_orm,
)


class SqlAlchemyTimeEntryRepository(TenantScopedRepositorySupport, TimeEntryRepository):
    _repository_label = "TimeEntryRepository"
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, entry: TimeEntry) -> None:
        ctx = self._context(operation_label="access time entries")
        orm = time_entry_to_orm(entry)
        orm.tenant_id = ctx.tenant_id
        orm.organization_id = ctx.organization_id
        self.session.add(orm)

    def get(self, entry_id: str) -> TimeEntry | None:
        ctx = self._context(operation_label="access time entries")
        stmt = select(TimeEntryORM).where(
            TimeEntryORM.id == entry_id,
            TimeEntryORM.tenant_id == ctx.tenant_id,
            TimeEntryORM.organization_id == ctx.organization_id,
        )
        obj = self.session.execute(stmt).scalar_one_or_none()
        return time_entry_from_orm(obj) if obj else None

    def update(self, entry: TimeEntry) -> None:
        ctx = self._context(operation_label="access time entries")
        obj = self.session.execute(
            select(TimeEntryORM).where(
                TimeEntryORM.id == entry.id,
                TimeEntryORM.tenant_id == ctx.tenant_id,
                TimeEntryORM.organization_id == ctx.organization_id,
            )
        ).scalar_one_or_none()
        if obj is None:
            orm = time_entry_to_orm(entry)
            orm.tenant_id = ctx.tenant_id
            orm.organization_id = ctx.organization_id
            self.session.add(orm)
            return
        obj.organization_id = ctx.organization_id
        obj.work_allocation_id = entry.work_allocation_id
        obj.assignment_id = entry.assignment_id
        obj.entry_date = entry.entry_date
        obj.hours = entry.hours
        obj.note = entry.note
        obj.owner_type = entry.owner_type
        obj.owner_id = entry.owner_id
        obj.owner_label = entry.owner_label or None
        obj.scope_type = entry.scope_type
        obj.scope_id = entry.scope_id
        obj.employee_id = entry.employee_id
        obj.department_id = entry.department_id
        obj.department_name = entry.department_name or None
        obj.site_id = entry.site_id
        obj.site_name = entry.site_name or None
        obj.author_user_id = entry.author_user_id
        obj.author_username = entry.author_username
        obj.created_at = entry.created_at
        obj.updated_at = entry.updated_at

    def delete(self, entry_id: str) -> None:
        ctx = self._context(operation_label="access time entries")
        obj = self.session.execute(
            select(TimeEntryORM).where(
                TimeEntryORM.id == entry_id,
                TimeEntryORM.tenant_id == ctx.tenant_id,
                TimeEntryORM.organization_id == ctx.organization_id,
            )
        ).scalar_one_or_none()
        if obj is not None:
            self.session.delete(obj)

    def list_by_work_allocation(self, work_allocation_id: str) -> list[TimeEntry]:
        ctx = self._context(operation_label="access time entries")
        stmt = (
            select(TimeEntryORM)
            .where(
                TimeEntryORM.work_allocation_id == work_allocation_id,
                TimeEntryORM.tenant_id == ctx.tenant_id,
                TimeEntryORM.organization_id == ctx.organization_id,
            )
            .order_by(TimeEntryORM.entry_date.asc(), TimeEntryORM.created_at.asc())
        )
        rows = self.session.execute(stmt).scalars().all()
        return [time_entry_from_orm(row) for row in rows]

    def list_for_organization(self, organization_id: str) -> list[TimeEntry]:
        ctx = self._context(operation_label="access time entries")
        stmt = (
            select(TimeEntryORM)
            .where(
                TimeEntryORM.organization_id == ctx.organization_id,
                TimeEntryORM.tenant_id == ctx.tenant_id,
            )
            .order_by(TimeEntryORM.entry_date.desc(), TimeEntryORM.created_at.desc())
        )
        rows = self.session.execute(stmt).scalars().all()
        return [time_entry_from_orm(row) for row in rows]

    def delete_by_work_allocation(self, work_allocation_id: str) -> None:
        ctx = self._context(operation_label="access time entries")
        rows = self.session.execute(
            select(TimeEntryORM).where(
                TimeEntryORM.work_allocation_id == work_allocation_id,
                TimeEntryORM.tenant_id == ctx.tenant_id,
                TimeEntryORM.organization_id == ctx.organization_id,
            )
        ).scalars().all()
        for row in rows:
            self.session.delete(row)


class SqlAlchemyTimesheetPeriodRepository(
    TenantScopedRepositorySupport, TimesheetPeriodRepository
):
    _repository_label = "TimesheetPeriodRepository"
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, period: TimesheetPeriod) -> None:
        ctx = self._context(operation_label="access timesheet periods")
        orm = timesheet_period_to_orm(period)
        orm.tenant_id = ctx.tenant_id
        orm.organization_id = ctx.organization_id
        self.session.add(orm)

    def get(self, period_id: str) -> TimesheetPeriod | None:
        ctx = self._context(operation_label="access timesheet periods")
        stmt = select(TimesheetPeriodORM).where(
            TimesheetPeriodORM.id == period_id,
            TimesheetPeriodORM.tenant_id == ctx.tenant_id,
            TimesheetPeriodORM.organization_id == ctx.organization_id,
        )
        obj = self.session.execute(stmt).scalar_one_or_none()
        return timesheet_period_from_orm(obj) if obj else None

    def update(self, period: TimesheetPeriod) -> None:
        ctx = self._context(operation_label="access timesheet periods")
        obj = self.session.execute(
            select(TimesheetPeriodORM).where(
                TimesheetPeriodORM.id == period.id,
                TimesheetPeriodORM.tenant_id == ctx.tenant_id,
                TimesheetPeriodORM.organization_id == ctx.organization_id,
            )
        ).scalar_one_or_none()
        if obj is None:
            orm = timesheet_period_to_orm(period)
            orm.tenant_id = ctx.tenant_id
            orm.organization_id = ctx.organization_id
            self.session.add(orm)
            return
        obj.organization_id = ctx.organization_id
        obj.resource_id = period.resource_id
        obj.period_start = period.period_start
        obj.period_end = period.period_end
        obj.status = period.status
        obj.submitted_at = period.submitted_at
        obj.submitted_by_user_id = period.submitted_by_user_id
        obj.submitted_by_username = period.submitted_by_username
        obj.decided_at = period.decided_at
        obj.decided_by_user_id = period.decided_by_user_id
        obj.decided_by_username = period.decided_by_username
        obj.decision_note = period.decision_note
        obj.locked_at = period.locked_at

    def get_by_resource_period(self, resource_id: str, period_start: date) -> TimesheetPeriod | None:
        ctx = self._context(operation_label="access timesheet periods")
        stmt = select(TimesheetPeriodORM).where(
            TimesheetPeriodORM.resource_id == resource_id,
            TimesheetPeriodORM.period_start == period_start,
            TimesheetPeriodORM.tenant_id == ctx.tenant_id,
            TimesheetPeriodORM.organization_id == ctx.organization_id,
        )
        obj = self.session.execute(stmt).scalar_one_or_none()
        return timesheet_period_from_orm(obj) if obj else None

    def list_by_resource(self, resource_id: str) -> list[TimesheetPeriod]:
        ctx = self._context(operation_label="access timesheet periods")
        stmt = (
            select(TimesheetPeriodORM)
            .where(
                TimesheetPeriodORM.resource_id == resource_id,
                TimesheetPeriodORM.tenant_id == ctx.tenant_id,
                TimesheetPeriodORM.organization_id == ctx.organization_id,
            )
            .order_by(TimesheetPeriodORM.period_start.desc())
        )
        rows = self.session.execute(stmt).scalars().all()
        return [timesheet_period_from_orm(row) for row in rows]

    def list_review_candidates(
        self,
        *,
        organization_id: str | None = None,
        status: TimesheetPeriodStatus | None = None,
        limit: int | None = None,
    ) -> list[TimesheetPeriod]:
        ctx = self._context(operation_label="access timesheet periods")
        stmt = select(TimesheetPeriodORM).where(
            TimesheetPeriodORM.tenant_id == ctx.tenant_id,
            TimesheetPeriodORM.organization_id == ctx.organization_id,
        )
        if organization_id is not None and organization_id != ctx.organization_id:
            return []
        if status is not None:
            stmt = stmt.where(TimesheetPeriodORM.status == status)
        stmt = stmt.order_by(TimesheetPeriodORM.submitted_at.desc(), TimesheetPeriodORM.period_start.desc())
        if limit is not None:
            stmt = stmt.limit(limit)
        rows = self.session.execute(stmt).scalars().all()
        return [timesheet_period_from_orm(row) for row in rows]


__all__ = [
    "SqlAlchemyTimeEntryRepository",
    "SqlAlchemyTimesheetPeriodRepository",
]
