from __future__ import annotations

from sqlalchemy import and_, case, func, or_, select, union
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
        def build_entry_ownership(*, name: str, resource_ids=None):
            assignment_owner = aliased(
                TaskAssignmentORM, name=f"{name}_assignment_owner"
            )
            employee_owner = aliased(ResourceORM, name=f"{name}_employee_owner")
            assignment_stmt = (
                select(
                    TimeEntryORM.id.label("entry_id"),
                    assignment_owner.resource_id.label("resource_id"),
                )
                .join(assignment_owner, assignment_owner.id == allocation_id)
                .where(
                    TimeEntryORM.tenant_id == tenant_id,
                    TimeEntryORM.organization_id == organization_id,
                )
            )
            employee_stmt = (
                select(
                    TimeEntryORM.id.label("entry_id"),
                    employee_owner.id.label("resource_id"),
                )
                .join(
                    employee_owner,
                    and_(
                        employee_owner.employee_id == TimeEntryORM.employee_id,
                        employee_owner.tenant_id == tenant_id,
                        employee_owner.organization_id == organization_id,
                    ),
                )
                .where(
                    TimeEntryORM.tenant_id == tenant_id,
                    TimeEntryORM.organization_id == organization_id,
                    TimeEntryORM.employee_id.is_not(None),
                )
            )
            if resource_ids is not None:
                assignment_stmt = assignment_stmt.where(
                    assignment_owner.resource_id.in_(resource_ids)
                )
                employee_stmt = employee_stmt.where(employee_owner.id.in_(resource_ids))
            return union(assignment_stmt, employee_stmt).cte(name)

        entry_ownership = build_entry_ownership(name="review_entry_ownership")
        project_id = case(
            (
                (func.lower(func.coalesce(TimeEntryORM.scope_type, "")) == "project")
                & TimeEntryORM.scope_id.is_not(None),
                TimeEntryORM.scope_id,
            ),
            else_=TaskORM.project_id,
        )

        def joined(stmt, *, ownership=entry_ownership):
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
                    ownership,
                    ownership.c.resource_id == TimesheetPeriodORM.resource_id,
                )
                .join(
                    TimeEntryORM,
                    and_(
                        TimeEntryORM.id == ownership.c.entry_id,
                        TimeEntryORM.tenant_id == tenant_id,
                        TimeEntryORM.organization_id == organization_id,
                        TimeEntryORM.entry_date >= TimesheetPeriodORM.period_start,
                        TimeEntryORM.entry_date <= TimesheetPeriodORM.period_end,
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

        period_sort_expressions = {
            "resource": (func.lower(ResourceORM.name),),
            "title": (func.lower(ResourceORM.name),),
            "period": (TimesheetPeriodORM.period_start, TimesheetPeriodORM.period_end),
            "status": (TimesheetPeriodORM.status,),
            "statusLabel": (TimesheetPeriodORM.status,),
            "submittedAt": (TimesheetPeriodORM.submitted_at,),
            "metaText": (TimesheetPeriodORM.submitted_at,),
        }
        fast_page = (
            allowed_project_ids is None
            and not criteria.project_id
            and not criteria.search_text
            and criteria.sort.key in period_sort_expressions
        )
        summary_offset = (page - 1) * page_size
        if fast_page:
            scoped_periods = (
                select(TimesheetPeriodORM.id.label("period_id"))
                .select_from(TimesheetPeriodORM)
                .join(
                    ResourceORM,
                    and_(
                        ResourceORM.id == TimesheetPeriodORM.resource_id,
                        ResourceORM.tenant_id == tenant_id,
                        ResourceORM.organization_id == organization_id,
                    ),
                )
                .where(
                    TimesheetPeriodORM.tenant_id == tenant_id,
                    TimesheetPeriodORM.organization_id == organization_id,
                    *filters,
                )
            )
            total = int(
                self._session.scalar(
                    select(func.count()).select_from(scoped_periods.order_by(None).subquery())
                )
                or 0
            )
            selected_page = (
                scoped_periods.order_by(
                    *stable_order_by(
                        sort=criteria.sort,
                        expressions=period_sort_expressions,
                        default_key="submittedAt",
                        tie_breakers=(TimesheetPeriodORM.id,),
                    )
                )
                .offset(summary_offset)
                .limit(page_size)
                .cte("review_page_periods")
            )
            selected_period_ids = select(selected_page.c.period_id)
            selected_resource_ids = (
                select(TimesheetPeriodORM.resource_id)
                .join(
                    selected_page,
                    selected_page.c.period_id == TimesheetPeriodORM.id,
                )
            )
            page_entry_ownership = build_entry_ownership(
                name="review_page_entry_ownership",
                resource_ids=selected_resource_ids,
            )
            summary_offset = 0
        else:
            period_ids = (
                joined(select(TimesheetPeriodORM.id.label("period_id")))
                .where(*filters)
                .group_by(TimesheetPeriodORM.id)
                .subquery()
            )
            total = int(self._session.scalar(select(func.count()).select_from(period_ids)) or 0)
            selected_period_ids = select(period_ids.c.period_id)

        summary_ownership = page_entry_ownership if fast_page else entry_ownership
        project_ids_aggregate = (
            func.array_agg(func.distinct(project_id)).filter(project_id.is_not(None))
            if self._session.get_bind().dialect.name == "postgresql"
            else func.group_concat(func.distinct(project_id))
        )
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
                project_ids_aggregate.label("project_ids"),
            ),
            ownership=summary_ownership,
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
            .offset(summary_offset)
            .limit(page_size)
        ).all()

        def project_ids_from(value) -> tuple[str, ...]:
            if value is None:
                return ()
            values = value if isinstance(value, (list, tuple)) else str(value).split(",")
            return tuple(sorted({str(item) for item in values if str(item or "").strip()}))

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
                    project_ids=project_ids_from(row[18]),
                )
                for row in summary_rows
            ),
            total=total,
            page=page,
            page_size=page_size,
            sort=criteria.sort,
        )


__all__ = ["SqlAlchemyTimesheetReviewReader"]
