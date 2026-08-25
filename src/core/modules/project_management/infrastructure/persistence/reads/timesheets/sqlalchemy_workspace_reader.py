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

