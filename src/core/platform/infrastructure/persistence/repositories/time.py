from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.time.contracts import TimeEntryRepository, TimesheetPeriodRepository
from src.core.platform.time.domain import TimeEntry, TimesheetPeriod, TimesheetPeriodStatus
from src.core.platform.infrastructure.persistence.orm.time import TimeEntryORM, TimesheetPeriodORM
from src.core.platform.infrastructure.persistence.mappers.time import (
    time_entry_from_orm,
    time_entry_to_orm,
    timesheet_period_from_orm,
    timesheet_period_to_orm,
)


class SqlAlchemyTimeEntryRepository(TimeEntryRepository):
    session: Session

    def __init__(self, session: Session, *, tenant_id_provider=None) -> None:
        self.session = session
        self._tenant_id_provider = tenant_id_provider or (lambda: None)

    def add(self, entry: TimeEntry) -> None:
        orm = time_entry_to_orm(entry)
        if orm.tenant_id is None:
            orm.tenant_id = self._tenant_id_provider()
        self.session.add(orm)

    def get(self, entry_id: str) -> TimeEntry | None:
        obj = self.session.get(TimeEntryORM, entry_id)
        return time_entry_from_orm(obj) if obj else None

    def update(self, entry: TimeEntry) -> None:
        orm = time_entry_to_orm(entry)
        if orm.tenant_id is None:
            existing = self.session.get(TimeEntryORM, entry.id)
            orm.tenant_id = (existing.tenant_id if existing is not None else None) or self._tenant_id_provider()
        self.session.merge(orm)

    def delete(self, entry_id: str) -> None:
        self.session.query(TimeEntryORM).filter_by(id=entry_id).delete()

    def list_by_work_allocation(self, work_allocation_id: str) -> list[TimeEntry]:
        stmt = (
            select(TimeEntryORM)
            .where(TimeEntryORM.work_allocation_id == work_allocation_id)
            .order_by(TimeEntryORM.entry_date.asc(), TimeEntryORM.created_at.asc())
        )
        rows = self.session.execute(stmt).scalars().all()
        return [time_entry_from_orm(row) for row in rows]

    def list_for_organization(self, organization_id: str) -> list[TimeEntry]:
        stmt = (
            select(TimeEntryORM)
            .where(TimeEntryORM.organization_id == organization_id)
            .order_by(TimeEntryORM.entry_date.desc(), TimeEntryORM.created_at.desc())
        )
        rows = self.session.execute(stmt).scalars().all()
        return [time_entry_from_orm(row) for row in rows]

    def delete_by_work_allocation(self, work_allocation_id: str) -> None:
        self.session.query(TimeEntryORM).filter_by(work_allocation_id=work_allocation_id).delete()


class SqlAlchemyTimesheetPeriodRepository(TimesheetPeriodRepository):
    session: Session

    def __init__(self, session: Session, *, tenant_id_provider=None) -> None:
        self.session = session
        self._tenant_id_provider = tenant_id_provider or (lambda: None)

    def add(self, period: TimesheetPeriod) -> None:
        orm = timesheet_period_to_orm(period)
        if orm.tenant_id is None:
            orm.tenant_id = self._tenant_id_provider()
        self.session.add(orm)

    def get(self, period_id: str) -> TimesheetPeriod | None:
        obj = self.session.get(TimesheetPeriodORM, period_id)
        return timesheet_period_from_orm(obj) if obj else None

    def update(self, period: TimesheetPeriod) -> None:
        orm = timesheet_period_to_orm(period)
        if orm.tenant_id is None:
            existing = self.session.get(TimesheetPeriodORM, period.id)
            orm.tenant_id = (existing.tenant_id if existing is not None else None) or self._tenant_id_provider()
        self.session.merge(orm)

    def get_by_resource_period(self, resource_id: str, period_start: date) -> TimesheetPeriod | None:
        stmt = select(TimesheetPeriodORM).where(
            TimesheetPeriodORM.resource_id == resource_id,
            TimesheetPeriodORM.period_start == period_start,
        )
        obj = self.session.execute(stmt).scalar_one_or_none()
        return timesheet_period_from_orm(obj) if obj else None

    def list_by_resource(self, resource_id: str) -> list[TimesheetPeriod]:
        stmt = (
            select(TimesheetPeriodORM)
            .where(TimesheetPeriodORM.resource_id == resource_id)
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
        stmt = select(TimesheetPeriodORM)
        if organization_id is not None:
            stmt = stmt.where(TimesheetPeriodORM.organization_id == organization_id)
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
