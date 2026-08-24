from __future__ import annotations

from collections import defaultdict

from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.orm import Session, aliased

from src.core.modules.project_management.contracts.reads.timesheets import (
    TimesheetReviewCriteria,
    TimesheetReviewInspectorFact,
    TimesheetReviewQueueFact,
    TimesheetReviewReadPage,
)
from src.core.modules.project_management.infrastructure.persistence.reads.sorting import stable_order_by
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskORM,
)
from src.core.platform.infrastructure.persistence.orm.time_management.time.time import (
    TimeEntryORM,
    TimesheetPeriodORM,
)


class SqlAlchemyTimesheetReviewReader:
    """Bounded PM review projection over the platform-owned TimesheetPeriod."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def read_item(
        self,
        *,
        item_id: str,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
    ) -> TimesheetReviewInspectorFact | None:
        page = self.read_page(
            tenant_id=tenant_id,
            organization_id=organization_id,
            allowed_project_ids=allowed_project_ids,
            criteria=TimesheetReviewCriteria(item_id=str(item_id or "").strip(), status=None),
            page=1,
            page_size=1,
        )
        return TimesheetReviewInspectorFact(page.items[0]) if page.items else None

    def read_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        criteria: TimesheetReviewCriteria,
        page: int,
        page_size: int,
    ) -> TimesheetReviewReadPage:
        if allowed_project_ids == ():
            return TimesheetReviewReadPage(
                page=page,
                page_size=page_size,
                sort=criteria.sort,
            )

        allocation_id = func.coalesce(
            TimeEntryORM.assignment_id,
            TimeEntryORM.work_allocation_id,
        )
        resource_assignment = aliased(TaskAssignmentORM)
        entry_matches_resource = or_(
            and_(
                TimeEntryORM.employee_id.is_not(None),
                ResourceORM.employee_id.is_not(None),
                TimeEntryORM.employee_id == ResourceORM.employee_id,
            ),
            exists(
                select(resource_assignment.id).where(
                    resource_assignment.id == allocation_id,
                    resource_assignment.resource_id == TimesheetPeriodORM.resource_id,
                )
            ),
        )
        project_id = case(
            (
                (func.lower(func.coalesce(TimeEntryORM.scope_type, "")) == "project")
                & TimeEntryORM.scope_id.is_not(None),
                TimeEntryORM.scope_id,
            ),
            else_=TaskORM.project_id,
        )

        def joined(stmt):
            return (
                stmt.select_from(TimesheetPeriodORM)
                .join(
                    ResourceORM,
                    and_(
                        ResourceORM.id == TimesheetPeriodORM.resource_id,
                        ResourceORM.tenant_id == tenant_id,
                        ResourceORM.organization_id == organization_id,
                    ),
                )
                .join(
                    TimeEntryORM,
                    and_(
                        TimeEntryORM.tenant_id == tenant_id,
                        TimeEntryORM.organization_id == organization_id,
                        TimeEntryORM.entry_date >= TimesheetPeriodORM.period_start,
                        TimeEntryORM.entry_date <= TimesheetPeriodORM.period_end,
                        entry_matches_resource,
                    ),
                )
                .outerjoin(
                    TaskAssignmentORM,
                    and_(
                        TaskAssignmentORM.id == allocation_id,
                        TaskAssignmentORM.resource_id == TimesheetPeriodORM.resource_id,
                    ),
                )
                .outerjoin(
                    TaskORM,
                    and_(
                        TaskORM.id == TaskAssignmentORM.task_id,
                    ),
                )
                .outerjoin(
                    ProjectORM,
                    and_(
                        ProjectORM.id == project_id,
                        ProjectORM.tenant_id == tenant_id,
                        ProjectORM.organization_id == organization_id,
                    ),
                )
                .where(
                    TimesheetPeriodORM.tenant_id == tenant_id,
                    TimesheetPeriodORM.organization_id == organization_id,
                )
            )

        visibility_filter = None
        if allowed_project_ids is not None:
            visibility_ids = (
                joined(select(TimesheetPeriodORM.id.label("period_id")))
                .group_by(TimesheetPeriodORM.id)
                .having(
                    func.count(
                        func.distinct(
                            case(
                                (
                                    and_(
                                        project_id.is_not(None),
                                        project_id.not_in(allowed_project_ids),
                                    ),
                                    TimeEntryORM.id,
                                )
                            )
                        )
                    )
                    == 0,
                    func.count(
                        func.distinct(
                            case(
                                (project_id.in_(allowed_project_ids), TimeEntryORM.id)
                            )
                        )
                    )
                    > 0,
                )
                .subquery()
            )
            visibility_filter = TimesheetPeriodORM.id.in_(
                select(visibility_ids.c.period_id)
            )

        filters = []
        if visibility_filter is not None:
            filters.append(visibility_filter)
        if criteria.item_id:
            filters.append(TimesheetPeriodORM.id == criteria.item_id)
        if criteria.status is not None:
            filters.append(TimesheetPeriodORM.status == criteria.status)
        if criteria.resource_id:
            filters.append(TimesheetPeriodORM.resource_id == criteria.resource_id)
        if criteria.period_start_from is not None:
            filters.append(TimesheetPeriodORM.period_start >= criteria.period_start_from)
        if criteria.period_start_to is not None:
            filters.append(TimesheetPeriodORM.period_start <= criteria.period_start_to)
        if criteria.project_id:
            filters.append(project_id == criteria.project_id)
        if criteria.search_text:
            escaped = (
                criteria.search_text.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            pattern = f"%{escaped.lower()}%"
            filters.append(
                or_(
                    func.lower(ResourceORM.name).like(pattern, escape="\\"),
                    func.lower(func.coalesce(ResourceORM.resource_code, "")).like(
                        pattern, escape="\\"
                    ),
                    func.lower(func.coalesce(ProjectORM.name, "")).like(
                        pattern, escape="\\"
                    ),
                    func.lower(func.coalesce(ProjectORM.project_code, "")).like(
                        pattern, escape="\\"
                    ),
                )
            )

        period_ids = (
            joined(select(TimesheetPeriodORM.id.label("period_id")))
            .where(*filters)
            .group_by(TimesheetPeriodORM.id)
            .subquery()
        )
        total = int(self._session.scalar(select(func.count()).select_from(period_ids)) or 0)
        selected_period_ids = select(period_ids.c.period_id)

        summary_stmt = joined(
            select(
                TimesheetPeriodORM.id,
                TimesheetPeriodORM.version,
                TimesheetPeriodORM.resource_id,
                ResourceORM.name,
                ResourceORM.resource_code,
                TimesheetPeriodORM.period_start,
                TimesheetPeriodORM.period_end,
                TimesheetPeriodORM.status,
                TimesheetPeriodORM.submitted_at,
                TimesheetPeriodORM.submitted_by_username,
                TimesheetPeriodORM.decided_at,
                TimesheetPeriodORM.decided_by_username,
                TimesheetPeriodORM.decision_note,
                func.count(func.distinct(TimeEntryORM.id)).label("entry_count"),
                func.sum(TimeEntryORM.hours).label("total_hours"),
                func.count(func.distinct(project_id)).label("project_count"),
                func.count(func.distinct(TaskORM.id)).label("task_count"),
                func.count(
                    func.distinct(case((TaskORM.id.is_(None), TimeEntryORM.id)))
                ).label("generic_entry_count"),
            )
        ).where(TimesheetPeriodORM.id.in_(selected_period_ids)).group_by(
            TimesheetPeriodORM.id,
            TimesheetPeriodORM.version,
            TimesheetPeriodORM.resource_id,
            ResourceORM.name,
            ResourceORM.resource_code,
            TimesheetPeriodORM.period_start,
            TimesheetPeriodORM.period_end,
            TimesheetPeriodORM.status,
            TimesheetPeriodORM.submitted_at,
            TimesheetPeriodORM.submitted_by_username,
            TimesheetPeriodORM.decided_at,
            TimesheetPeriodORM.decided_by_username,
            TimesheetPeriodORM.decision_note,
        )
        sort_expressions = {
            "resource": (func.lower(ResourceORM.name),),
            "title": (func.lower(ResourceORM.name),),
            "period": (TimesheetPeriodORM.period_start, TimesheetPeriodORM.period_end),
            "status": (TimesheetPeriodORM.status,),
            "statusLabel": (TimesheetPeriodORM.status,),
            "totalHours": (func.sum(TimeEntryORM.hours),),
            "supportingText": (func.sum(TimeEntryORM.hours),),
            "submittedAt": (TimesheetPeriodORM.submitted_at,),
            "metaText": (TimesheetPeriodORM.submitted_at,),
        }
        summary_rows = self._session.execute(
            summary_stmt.order_by(
                *stable_order_by(
                    sort=criteria.sort,
                    expressions=sort_expressions,
                    default_key="submittedAt",
                    tie_breakers=(TimesheetPeriodORM.id,),
                )
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        page_period_ids = tuple(str(row[0]) for row in summary_rows)
        projects_by_period: dict[str, set[str]] = defaultdict(set)
        if page_period_ids:
            project_rows = self._session.execute(
                joined(
                    select(
                        TimesheetPeriodORM.id,
                        project_id.label("project_id"),
                    )
                )
                .where(
                    TimesheetPeriodORM.id.in_(page_period_ids),
                    project_id.is_not(None),
                )
                .distinct()
            ).all()
            for period_id_value, project_id_value in project_rows:
                projects_by_period[str(period_id_value)].add(str(project_id_value))

        return TimesheetReviewReadPage(
            items=tuple(
                TimesheetReviewQueueFact(
                    item_id=str(row[0]),
                    timesheet_period_id=str(row[0]),
                    version=int(row[1]),
                    resource_id=str(row[2]),
                    resource_name=str(row[3] or row[2]),
                    resource_code=str(row[4] or ""),
                    period_start=row[5],
                    period_end=row[6],
                    status=row[7],
                    submitted_at=row[8],
                    submitted_by_username=row[9],
                    decided_at=row[10],
                    decided_by_username=row[11],
                    decision_note=row[12],
                    entry_count=int(row[13] or 0),
                    total_hours=float(row[14] or 0.0),
                    project_count=int(row[15] or 0),
                    task_count=int(row[16] or 0),
                    generic_entry_count=int(row[17] or 0),
                    project_ids=tuple(sorted(projects_by_period[str(row[0])])),
                )
                for row in summary_rows
            ),
            total=total,
            page=page,
            page_size=page_size,
            sort=criteria.sort,
        )


__all__ = ["SqlAlchemyTimesheetReviewReader"]
