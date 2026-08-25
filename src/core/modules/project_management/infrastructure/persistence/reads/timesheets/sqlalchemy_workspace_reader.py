from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.timesheets import (
    TimesheetEntryCriteria,
    TimesheetEntryFact,
    TimesheetEntryReadPage,
    TimesheetHistoryCriteria,
    TimesheetHistoryReadPage,
    TimesheetPeriodFact,
    TimesheetResourceFact,
    TimesheetResourceReadPage,
    TimesheetResourceSelectorCriteria,
    TimesheetScope,
)
from src.core.modules.project_management.domain.resources import (
    TimeReportingEligibilityPolicy,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskORM,
)
from src.core.modules.project_management.infrastructure.persistence.reads.sorting import stable_order_by
from src.core.platform.domain.time_management.time import (
    TimesheetPeriodStatus,
    coerce_timesheet_period_status,
)
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import EmployeeORM
from src.core.platform.infrastructure.persistence.orm.time_management.time.time import (
    TimeEntryORM,
    TimesheetPeriodORM,
)


def _decimal_hours(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _period_bounds(value: date) -> tuple[date, date]:
    start = value.replace(day=1)
    return start, start.replace(day=calendar.monthrange(start.year, start.month)[1])


class SqlAlchemyTimesheetWorkspaceReader:
    """Bounded resource-centric Timesheets projection."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    @staticmethod
    def _eligibility_filters(*, include_inactive: bool = False) -> list[object]:
        filters: list[object] = [
            ResourceORM.kind.in_(tuple(TimeReportingEligibilityPolicy.ELIGIBLE_KINDS)),
            ResourceORM.worker_type.in_(tuple(TimeReportingEligibilityPolicy.ELIGIBLE_WORKER_TYPES)),
            ResourceORM.cost_type.in_(tuple(TimeReportingEligibilityPolicy.ELIGIBLE_COST_TYPES)),
        ]
        if not include_inactive:
            filters.append(ResourceORM.is_active.is_(True))
        return filters

    @staticmethod
    def _resource_columns():
        return (
            ResourceORM.id,
            ResourceORM.name,
            ResourceORM.resource_code,
            ResourceORM.kind,
            ResourceORM.worker_type,
            ResourceORM.employee_id,
            EmployeeORM.user_id,
            ResourceORM.is_active,
        )

    @staticmethod
    def _resource_fact(row) -> TimesheetResourceFact:
        return TimesheetResourceFact(
            resource_id=str(row[0]),
            resource_name=str(row[1] or row[0]),
            resource_code=str(row[2] or ""),
            kind=str(getattr(row[3], "value", row[3]) or ""),
            worker_type=str(getattr(row[4], "value", row[4]) or ""),
            employee_id=str(row[5]) if row[5] else None,
            identity_user_id=str(row[6]) if row[6] else None,
            is_active=bool(row[7]),
        )

    def resolve_mine_resource(
        self,
        *,
        user_id: str,
        tenant_id: str,
        organization_id: str,
    ) -> TimesheetResourceFact | None:
        rows = self._session.execute(
            select(*self._resource_columns())
            .select_from(ResourceORM)
            .join(EmployeeORM, EmployeeORM.id == ResourceORM.employee_id)
            .where(
                ResourceORM.tenant_id == tenant_id,
                ResourceORM.organization_id == organization_id,
                EmployeeORM.user_id == user_id,
                EmployeeORM.tenant_id == tenant_id,
                EmployeeORM.organization_id == organization_id,
                EmployeeORM.is_active.is_(True),
                *self._eligibility_filters(),
            )
            .order_by(ResourceORM.id.asc())
            .limit(2)
        ).all()
        if len(rows) != 1:
            return None
        return self._resource_fact(rows[0])

    def _resource_scope_stmt(
        self,
        *,
        scope: TimesheetScope,
        actor_user_id: str,
        explicit_team_project_ids: tuple[str, ...],
        tenant_id: str,
        organization_id: str,
        include_inactive: bool,
        resource_id: str | None = None,
    ):
        stmt = (
            select(*self._resource_columns())
            .select_from(ResourceORM)
            .outerjoin(EmployeeORM, EmployeeORM.id == ResourceORM.employee_id)
            .where(
                ResourceORM.tenant_id == tenant_id,
                ResourceORM.organization_id == organization_id,
                *self._eligibility_filters(include_inactive=include_inactive),
            )
        )
        if resource_id:
            stmt = stmt.where(ResourceORM.id == resource_id)
        if scope == TimesheetScope.TEAM:
            team_predicates: list[object] = [ProjectORM.manager_user_id == actor_user_id]
            if explicit_team_project_ids:
                team_predicates.append(ProjectORM.id.in_(explicit_team_project_ids))
            stmt = (
                stmt.join(TaskAssignmentORM, TaskAssignmentORM.resource_id == ResourceORM.id)
                .join(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
                .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
                .where(
                    ProjectORM.tenant_id == tenant_id,
                    ProjectORM.organization_id == organization_id,
                    or_(*team_predicates),
                )
                .distinct()
            )
        return stmt

    def read_resource_page(
        self,
        *,
        scope: TimesheetScope,
        actor_user_id: str,
        explicit_team_project_ids: tuple[str, ...],
        tenant_id: str,
        organization_id: str,
        criteria: TimesheetResourceSelectorCriteria,
        page: int,
        page_size: int,
    ) -> TimesheetResourceReadPage:
        if scope == TimesheetScope.MINE:
            mine = self.resolve_mine_resource(
                user_id=actor_user_id,
                tenant_id=tenant_id,
                organization_id=organization_id,
            )
            return TimesheetResourceReadPage(
                items=(mine,) if mine else (),
                total=1 if mine else 0,
                page=1,
                page_size=page_size,
                sort=criteria.sort,
            )
        stmt = self._resource_scope_stmt(
            scope=scope,
            actor_user_id=actor_user_id,
            explicit_team_project_ids=explicit_team_project_ids,
            tenant_id=tenant_id,
            organization_id=organization_id,
            include_inactive=criteria.include_inactive,
        )
        if criteria.search_text:
            escaped = criteria.search_text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(func.coalesce(ResourceORM.name, "")).like(pattern, escape="\\"),
                    func.lower(func.coalesce(ResourceORM.resource_code, "")).like(pattern, escape="\\"),
                )
            )
        total = int(
            self._session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
            or 0
        )
        rows = self._session.execute(
            stmt.order_by(
                *stable_order_by(
                    sort=criteria.sort,
                    expressions={
                        "resource": (func.lower(ResourceORM.name),),
                        "code": (func.lower(func.coalesce(ResourceORM.resource_code, "")),),
                    },
                    default_key="resource",
                    tie_breakers=(ResourceORM.id,),
                )
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return TimesheetResourceReadPage(
            items=tuple(self._resource_fact(row) for row in rows),
            total=total,
            page=page,
            page_size=page_size,
            sort=criteria.sort,
        )

    def read_resource_in_scope(
        self,
        *,
        scope: TimesheetScope,
        resource_id: str,
        actor_user_id: str,
        explicit_team_project_ids: tuple[str, ...],
        tenant_id: str,
        organization_id: str,
    ) -> TimesheetResourceFact | None:
        if scope == TimesheetScope.MINE:
            mine = self.resolve_mine_resource(
                user_id=actor_user_id,
                tenant_id=tenant_id,
                organization_id=organization_id,
            )
            return mine if mine and mine.resource_id == resource_id else None
        row = self._session.execute(
            self._resource_scope_stmt(
                scope=scope,
                actor_user_id=actor_user_id,
                explicit_team_project_ids=explicit_team_project_ids,
                tenant_id=tenant_id,
                organization_id=organization_id,
                include_inactive=False,
                resource_id=resource_id,
            ).limit(1)
        ).one_or_none()
        return self._resource_fact(row) if row else None

    @staticmethod
    def _project_id_expression():
        return case(
            (
                and_(
                    func.lower(func.coalesce(TimeEntryORM.scope_type, "")) == "project",
                    TimeEntryORM.scope_id.is_not(None),
                ),
                TimeEntryORM.scope_id,
            ),
            else_=TaskORM.project_id,
        )

    @staticmethod
    def _entry_joined(stmt, *, resource: TimesheetResourceFact):
        allocation_id = func.coalesce(TimeEntryORM.assignment_id, TimeEntryORM.work_allocation_id)
        owner_filters: list[object] = [TaskAssignmentORM.resource_id == resource.resource_id]
        if resource.employee_id:
            owner_filters.append(TimeEntryORM.employee_id == resource.employee_id)
        return (
            stmt.select_from(TimeEntryORM)
            .outerjoin(TaskAssignmentORM, TaskAssignmentORM.id == allocation_id)
            .outerjoin(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
            .outerjoin(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .where(or_(*owner_filters))
        )

    @staticmethod
    def _entry_filters(*, tenant_id: str, organization_id: str, period_start: date):
        start, end = _period_bounds(period_start)
        return [
            TimeEntryORM.tenant_id == tenant_id,
            TimeEntryORM.organization_id == organization_id,
            TimeEntryORM.entry_date >= start,
            TimeEntryORM.entry_date <= end,
        ]

    def read_period(
        self,
        *,
        resource: TimesheetResourceFact,
        tenant_id: str,
        organization_id: str,
        period_start: date,
    ) -> TimesheetPeriodFact:
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
                TimesheetPeriodORM.resource_id == resource.resource_id,
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
                resource=resource,
            ).where(
                *self._entry_filters(
                    tenant_id=tenant_id,
                    organization_id=organization_id,
                    period_start=start,
                )
            )
        ).one()
        return TimesheetPeriodFact(
            period_id=str(period[0]) if period else "",
            resource_id=resource.resource_id,
            resource_name=resource.resource_name,
            resource_code=resource.resource_code,
            resource_kind=resource.kind,
            worker_type=resource.worker_type,
            period_start=start,
            period_end=end,
            status=coerce_timesheet_period_status(period[1]) if period else TimesheetPeriodStatus.OPEN,
            version=int(period[2]) if period else 1,
            submitted_at=period[3] if period else None,
            decided_at=period[4] if period else None,
            decision_note=str(period[5] or "") if period else "",
            locked_at=period[6] if period else None,
            total_hours=_decimal_hours(aggregate[0]),
            entry_count=int(aggregate[1] or 0),
            project_count=int(aggregate[2] or 0),
            task_count=int(aggregate[3] or 0),
        )

    def read_entries(
        self,
        *,
        resource: TimesheetResourceFact,
        tenant_id: str,
        organization_id: str,
        visible_project_ids: tuple[str, ...] | None,
        criteria: TimesheetEntryCriteria,
        page: int,
        page_size: int,
    ) -> TimesheetEntryReadPage:
        project_id = self._project_id_expression()
        filters = self._entry_filters(
            tenant_id=tenant_id,
            organization_id=organization_id,
            period_start=criteria.period_start,
        )
        if criteria.project_id:
            filters.append(project_id == criteria.project_id)
        if criteria.task_id:
            filters.append(TaskORM.id == criteria.task_id)
        if criteria.work_date_from:
            filters.append(TimeEntryORM.entry_date >= criteria.work_date_from)
        if criteria.work_date_to:
            filters.append(TimeEntryORM.entry_date <= criteria.work_date_to)
        visible = project_id.in_(visible_project_ids) if visible_project_ids is not None else None
        if criteria.search_text:
            escaped = criteria.search_text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped.lower()}%"
            identity_search = or_(
                func.lower(func.coalesce(ProjectORM.name, "")).like(pattern, escape="\\"),
                func.lower(func.coalesce(ProjectORM.project_code, "")).like(pattern, escape="\\"),
                func.lower(func.coalesce(TaskORM.name, "")).like(pattern, escape="\\"),
                func.lower(func.coalesce(TaskORM.task_code, "")).like(pattern, escape="\\"),
            )
            filters.append(
                or_(
                    and_(visible, identity_search) if visible is not None else identity_search,
                    func.lower(func.coalesce(TimeEntryORM.note, "")).like(pattern, escape="\\"),
                )
            )
        total = int(
            self._session.scalar(
                self._entry_joined(
                    select(func.count(func.distinct(TimeEntryORM.id))), resource=resource
                ).where(*filters)
            )
            or 0
        )
        output_project_id = project_id
        output_project_code = func.coalesce(ProjectORM.project_code, "")
        output_project_name = func.coalesce(ProjectORM.name, "General")
        output_task_id = TaskORM.id
        output_task_code = func.coalesce(TaskORM.task_code, "")
        output_task_name = func.coalesce(TaskORM.name, "Project Work")
        if visible is not None:
            output_project_id = case((visible, project_id), else_=None)
            output_project_code = case((visible, output_project_code), else_="")
            output_project_name = case(
                (project_id.is_(None), "General"),
                (visible, output_project_name),
                else_="Restricted project",
            )
            output_task_id = case((visible, TaskORM.id), else_=None)
            output_task_code = case((visible, output_task_code), else_="")
            output_task_name = case((visible, output_task_name), else_="Restricted task")
        stmt = self._entry_joined(
            select(
                TimeEntryORM.id,
                func.coalesce(TimeEntryORM.assignment_id, TimeEntryORM.work_allocation_id),
                TimeEntryORM.entry_date,
                TimeEntryORM.hours,
                TimeEntryORM.note,
                output_project_id,
                output_project_code,
                output_project_name,
                output_task_id,
                output_task_code,
                output_task_name,
                TimeEntryORM.updated_at,
            ),
            resource=resource,
        ).where(*filters)
        rows = self._session.execute(
            stmt.order_by(
                *stable_order_by(
                    sort=criteria.sort,
                    expressions={
                        "date": (TimeEntryORM.entry_date,),
                        "project": (func.lower(output_project_name),),
                        "task": (func.lower(output_task_name),),
                        "hours": (TimeEntryORM.hours,),
                    },
                    default_key="date",
                    tie_breakers=(TimeEntryORM.id,),
                )
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return TimesheetEntryReadPage(
            items=tuple(
                TimesheetEntryFact(
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
        resource: TimesheetResourceFact,
        tenant_id: str,
        organization_id: str,
        criteria: TimesheetHistoryCriteria,
        page: int,
        page_size: int,
    ) -> TimesheetHistoryReadPage:
        project_id = self._project_id_expression()
        allocation_id = func.coalesce(TimeEntryORM.assignment_id, TimeEntryORM.work_allocation_id)
        owner_filters: list[object] = [TaskAssignmentORM.resource_id == resource.resource_id]
        if resource.employee_id:
            owner_filters.append(TimeEntryORM.employee_id == resource.employee_id)
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
                TimesheetPeriodORM.resource_id == resource.resource_id,
                or_(*owner_filters),
            )
        )
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
                select(func.count()).select_from(
                    base.with_only_columns(TimesheetPeriodORM.id).subquery()
                )
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
        return TimesheetHistoryReadPage(
            items=tuple(
                TimesheetPeriodFact(
                    period_id=str(row[0]),
                    resource_id=resource.resource_id,
                    resource_name=resource.resource_name,
                    resource_code=resource.resource_code,
                    resource_kind=resource.kind,
                    worker_type=resource.worker_type,
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


__all__ = ["SqlAlchemyTimesheetWorkspaceReader"]
