from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.timesheets import (
    OwnerTimesheetEntryCriteria,
    OwnerTimesheetEntryFact,
    OwnerTimesheetEntryReadPage,
    OwnerTimesheetHistoryCriteria,
    OwnerTimesheetHistoryReadPage,
    OwnerTimesheetIdentityFact,
    OwnerTimesheetPeriodFact,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.resource import (
    ResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskORM,
)
from src.core.modules.project_management.infrastructure.persistence.reads.sorting import (
    stable_order_by,
)
from src.core.platform.domain.time_management.time import (
    TimesheetPeriodStatus,
    coerce_timesheet_period_status,
)
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import (
    EmployeeORM,
)
from src.core.platform.infrastructure.persistence.orm.time_management.time.time import (
    TimeEntryORM,
    TimesheetPeriodORM,
)


def _decimal_hours(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _period_bounds(value: date) -> tuple[date, date]:
    start = value.replace(day=1)
    return start, start.replace(day=calendar.monthrange(start.year, start.month)[1])


class SqlAlchemyOwnerTimesheetReader:
    """Owner-scoped, bounded projection over platform TimeEntry/TimesheetPeriod."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def resolve_identity(
        self,
        *,
        user_id: str,
        tenant_id: str,
        organization_id: str,
    ) -> OwnerTimesheetIdentityFact | None:
        rows = self._session.execute(
            select(
                EmployeeORM.id,
                ResourceORM.id,
                ResourceORM.name,
                ResourceORM.resource_code,
            )
            .join(
                ResourceORM,
                and_(
                    ResourceORM.employee_id == EmployeeORM.id,
                    ResourceORM.tenant_id == tenant_id,
                    ResourceORM.organization_id == organization_id,
                    ResourceORM.is_active.is_(True),
                ),
            )
            .where(
                EmployeeORM.user_id == user_id,
                EmployeeORM.tenant_id == tenant_id,
                EmployeeORM.organization_id == organization_id,
                EmployeeORM.is_active.is_(True),
            )
            .order_by(ResourceORM.id.asc())
            .limit(2)
        ).all()
        if len(rows) != 1:
            return None
        employee_id, resource_id, resource_name, resource_code = rows[0]
        return OwnerTimesheetIdentityFact(
            user_id=user_id,
            employee_id=str(employee_id),
            resource_id=str(resource_id),
            resource_name=str(resource_name or resource_id),
            resource_code=str(resource_code or ""),
        )

    @staticmethod
    def _project_id_expression():
        return case(
            (
                and_(
                    func.lower(func.coalesce(TimeEntryORM.scope_type, ""))
                    == "project",
                    TimeEntryORM.scope_id.is_not(None),
                ),
                TimeEntryORM.scope_id,
            ),
            else_=TaskORM.project_id,
        )

    @staticmethod
    def _entry_joined(stmt, *, identity: OwnerTimesheetIdentityFact):
        allocation_id = func.coalesce(
            TimeEntryORM.assignment_id,
            TimeEntryORM.work_allocation_id,
        )
        return (
            stmt.select_from(TimeEntryORM)
            .outerjoin(TaskAssignmentORM, TaskAssignmentORM.id == allocation_id)
            .outerjoin(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
            .outerjoin(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .where(
                or_(
                    TimeEntryORM.employee_id == identity.employee_id,
                    TaskAssignmentORM.resource_id == identity.resource_id,
                )
            )
        )

    def _entry_filters(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        period_start: date,
        allowed_project_ids: tuple[str, ...] | None,
    ) -> list[object]:
        start, end = _period_bounds(period_start)
        filters: list[object] = [
            TimeEntryORM.tenant_id == tenant_id,
            TimeEntryORM.organization_id == organization_id,
            TimeEntryORM.entry_date >= start,
            TimeEntryORM.entry_date <= end,
        ]
        if allowed_project_ids is not None:
            filters.append(self._project_id_expression().in_(allowed_project_ids))
        return filters

    def read_period(
        self,
        *,
        identity: OwnerTimesheetIdentityFact,
        tenant_id: str,
        organization_id: str,
        period_start: date,
        allowed_project_ids: tuple[str, ...] | None,
    ) -> OwnerTimesheetPeriodFact:
        start, end = _period_bounds(period_start)
        period = self._session.execute(
            select(
                TimesheetPeriodORM.id,
                TimesheetPeriodORM.status,
                TimesheetPeriodORM.version,
                TimesheetPeriodORM.submitted_at,
                TimesheetPeriodORM.decided_at,
                TimesheetPeriodORM.decision_note,
                TimesheetPeriodORM.locked_at,
            ).where(
                TimesheetPeriodORM.tenant_id == tenant_id,
                TimesheetPeriodORM.organization_id == organization_id,
                TimesheetPeriodORM.resource_id == identity.resource_id,
                TimesheetPeriodORM.period_start == start,
            )
        ).one_or_none()
        project_id = self._project_id_expression()
        aggregate = self._session.execute(
            self._entry_joined(
                select(
                    func.coalesce(func.sum(TimeEntryORM.hours), 0),
                    func.count(func.distinct(TimeEntryORM.id)),
                    func.count(func.distinct(project_id)),
                    func.count(func.distinct(TaskORM.id)),
                ),
                identity=identity,
            ).where(
                *self._entry_filters(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    period_start=start,
                    allowed_project_ids=allowed_project_ids,
                )
            )
        ).one()
        return OwnerTimesheetPeriodFact(
            period_id=str(period[0]) if period is not None else "",
            resource_id=identity.resource_id,
            resource_name=identity.resource_name,
            period_start=start,
            period_end=end,
            status=(
                coerce_timesheet_period_status(period[1])
                if period is not None
                else TimesheetPeriodStatus.OPEN
            ),
            version=int(period[2]) if period is not None else 1,
            submitted_at=period[3] if period is not None else None,
            decided_at=period[4] if period is not None else None,
            decision_note=str(period[5] or "") if period is not None else "",
            locked_at=period[6] if period is not None else None,
            total_hours=_decimal_hours(aggregate[0]),
            entry_count=int(aggregate[1] or 0),
            project_count=int(aggregate[2] or 0),
            task_count=int(aggregate[3] or 0),
        )

    def read_entries(
        self,
        *,
        identity: OwnerTimesheetIdentityFact,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        criteria: OwnerTimesheetEntryCriteria,
        page: int,
        page_size: int,
    ) -> OwnerTimesheetEntryReadPage:
        if allowed_project_ids == ():
            return OwnerTimesheetEntryReadPage(
                page=page,
                page_size=page_size,
                sort=criteria.sort,
            )
        project_id = self._project_id_expression()
        filters = self._entry_filters(
            tenant_id=tenant_id,
            organization_id=organization_id,
            period_start=criteria.period_start,
            allowed_project_ids=allowed_project_ids,
        )
        if criteria.project_id:
            filters.append(project_id == criteria.project_id)
        if criteria.task_id:
            filters.append(TaskORM.id == criteria.task_id)
        if criteria.work_date_from:
            filters.append(TimeEntryORM.entry_date >= criteria.work_date_from)
        if criteria.work_date_to:
            filters.append(TimeEntryORM.entry_date <= criteria.work_date_to)
        if criteria.search_text:
            escaped = (
                criteria.search_text.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            pattern = f"%{escaped.lower()}%"
            filters.append(
                or_(
                    func.lower(func.coalesce(ProjectORM.name, "")).like(
                        pattern, escape="\\"
                    ),
                    func.lower(func.coalesce(ProjectORM.project_code, "")).like(
                        pattern, escape="\\"
                    ),
                    func.lower(func.coalesce(TaskORM.name, "")).like(
                        pattern, escape="\\"
                    ),
                    func.lower(func.coalesce(TaskORM.task_code, "")).like(
                        pattern, escape="\\"
                    ),
                    func.lower(func.coalesce(TimeEntryORM.note, "")).like(
                        pattern, escape="\\"
                    ),
                )
            )

        total = int(
            self._session.scalar(
                self._entry_joined(
                    select(func.count(func.distinct(TimeEntryORM.id))),
                    identity=identity,
                ).where(*filters)
            )
            or 0
        )
        stmt = self._entry_joined(
            select(
                TimeEntryORM.id,
                func.coalesce(
                    TimeEntryORM.assignment_id,
                    TimeEntryORM.work_allocation_id,
                ),
                TimeEntryORM.entry_date,
                TimeEntryORM.hours,
                TimeEntryORM.note,
                project_id.label("project_id"),
                ProjectORM.project_code,
                ProjectORM.name,
                TaskORM.id,
                TaskORM.task_code,
                TaskORM.name,
                TimeEntryORM.updated_at,
            ),
            identity=identity,
        ).where(*filters)
        rows = self._session.execute(
            stmt.order_by(
                *stable_order_by(
                    sort=criteria.sort,
                    expressions={
                        "date": (TimeEntryORM.entry_date,),
                        "project": (func.lower(func.coalesce(ProjectORM.name, "")),),
                        "task": (func.lower(func.coalesce(TaskORM.name, "")),),
                        "hours": (TimeEntryORM.hours,),
                    },
                    default_key="date",
                    tie_breakers=(TimeEntryORM.id,),
                )
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return OwnerTimesheetEntryReadPage(
            items=tuple(
                OwnerTimesheetEntryFact(
                    entry_id=str(row[0]),
                    assignment_id=str(row[1] or ""),
                    work_date=row[2],
                    hours=_decimal_hours(row[3]),
                    description=str(row[4] or ""),
                    project_id=str(row[5]) if row[5] else None,
                    project_code=str(row[6] or ""),
                    project_name=str(row[7] or "General"),
                    task_id=str(row[8]) if row[8] else None,
                    task_code=str(row[9] or ""),
                    task_name=str(row[10] or "Project Work"),
                    activity_type="task" if row[8] else "general",
                    updated_at=row[11],
                )
                for row in rows
            ),
            total=total,
            page=page,
            page_size=page_size,
            sort=criteria.sort,
        )

    def read_history(
        self,
        *,
        identity: OwnerTimesheetIdentityFact,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        criteria: OwnerTimesheetHistoryCriteria,
        page: int,
        page_size: int,
    ) -> OwnerTimesheetHistoryReadPage:
        if allowed_project_ids == ():
            return OwnerTimesheetHistoryReadPage(
                page=page,
                page_size=page_size,
                sort=criteria.sort,
            )
        project_id = self._project_id_expression()
        allocation_id = func.coalesce(
            TimeEntryORM.assignment_id,
            TimeEntryORM.work_allocation_id,
        )
        base = (
            select(
                TimesheetPeriodORM.id,
                TimesheetPeriodORM.period_start,
                TimesheetPeriodORM.period_end,
                TimesheetPeriodORM.status,
                TimesheetPeriodORM.version,
                TimesheetPeriodORM.submitted_at,
                TimesheetPeriodORM.decided_at,
                TimesheetPeriodORM.decision_note,
                TimesheetPeriodORM.locked_at,
                func.coalesce(func.sum(TimeEntryORM.hours), 0),
                func.count(func.distinct(TimeEntryORM.id)),
                func.count(func.distinct(project_id)),
                func.count(func.distinct(TaskORM.id)),
            )
            .select_from(TimesheetPeriodORM)
            .join(
                TimeEntryORM,
                and_(
                    TimeEntryORM.tenant_id == tenant_id,
                    TimeEntryORM.organization_id == organization_id,
                    TimeEntryORM.entry_date >= TimesheetPeriodORM.period_start,
                    TimeEntryORM.entry_date <= TimesheetPeriodORM.period_end,
                ),
            )
            .outerjoin(TaskAssignmentORM, TaskAssignmentORM.id == allocation_id)
            .outerjoin(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
            .outerjoin(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .where(
                TimesheetPeriodORM.tenant_id == tenant_id,
                TimesheetPeriodORM.organization_id == organization_id,
                TimesheetPeriodORM.resource_id == identity.resource_id,
                or_(
                    TimeEntryORM.employee_id == identity.employee_id,
                    TaskAssignmentORM.resource_id == identity.resource_id,
                ),
            )
        )
        if allowed_project_ids is not None:
            base = base.where(project_id.in_(allowed_project_ids))
        if criteria.status is not None:
            base = base.where(TimesheetPeriodORM.status == criteria.status)
        base = base.group_by(
            TimesheetPeriodORM.id,
            TimesheetPeriodORM.period_start,
            TimesheetPeriodORM.period_end,
            TimesheetPeriodORM.status,
            TimesheetPeriodORM.version,
            TimesheetPeriodORM.submitted_at,
            TimesheetPeriodORM.decided_at,
            TimesheetPeriodORM.decision_note,
            TimesheetPeriodORM.locked_at,
        )
        total = int(
            self._session.scalar(
                select(func.count()).select_from(base.with_only_columns(TimesheetPeriodORM.id).subquery())
            )
            or 0
        )
        rows = self._session.execute(
            base.order_by(
                *stable_order_by(
                    sort=criteria.sort,
                    expressions={
                        "period": (TimesheetPeriodORM.period_start,),
                        "status": (TimesheetPeriodORM.status,),
                        "totalHours": (func.sum(TimeEntryORM.hours),),
                        "submittedAt": (TimesheetPeriodORM.submitted_at,),
                    },
                    default_key="period",
                    tie_breakers=(TimesheetPeriodORM.id,),
                )
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return OwnerTimesheetHistoryReadPage(
            items=tuple(
                OwnerTimesheetPeriodFact(
                    period_id=str(row[0]),
                    resource_id=identity.resource_id,
                    resource_name=identity.resource_name,
                    period_start=row[1],
                    period_end=row[2],
                    status=coerce_timesheet_period_status(row[3]),
                    version=int(row[4]),
                    submitted_at=row[5],
                    decided_at=row[6],
                    decision_note=str(row[7] or ""),
                    locked_at=row[8],
                    total_hours=_decimal_hours(row[9]),
                    entry_count=int(row[10] or 0),
                    project_count=int(row[11] or 0),
                    task_count=int(row[12] or 0),
                )
                for row in rows
            ),
            total=total,
            page=page,
            page_size=page_size,
            sort=criteria.sort,
        )


__all__ = ["SqlAlchemyOwnerTimesheetReader"]
