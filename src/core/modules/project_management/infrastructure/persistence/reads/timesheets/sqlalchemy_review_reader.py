from __future__ import annotations

from collections import defaultdict

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.timesheets import (
    TimesheetReviewCriteria,
    TimesheetReviewReadPage,
)
from src.core.modules.project_management.infrastructure.persistence.reads.sorting import stable_order_by
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskORM,
)
from src.core.platform.application.time_management.time import TimesheetReviewQueueItem
from src.core.platform.infrastructure.persistence.orm.time_management.time.time import (
    TimeEntryORM,
    TimesheetPeriodORM,
)


class SqlAlchemyTimesheetReviewReader:
    def __init__(self, *, session: Session) -> None:
        self._session = session

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
        project_id = case(
            (
                (func.lower(func.coalesce(TimeEntryORM.scope_type, "")) == "project")
                & TimeEntryORM.scope_id.is_not(None),
                TimeEntryORM.scope_id,
            ),
            else_=TaskORM.project_id,
        )
        filters = [
            TimesheetPeriodORM.tenant_id == tenant_id,
            TimesheetPeriodORM.organization_id == organization_id,
            TimeEntryORM.tenant_id == tenant_id,
            TimeEntryORM.organization_id == organization_id,
            ResourceORM.tenant_id == tenant_id,
            ResourceORM.organization_id == organization_id,
            ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
        ]
        if criteria.status is not None:
            filters.append(TimesheetPeriodORM.status == criteria.status)
        if criteria.resource_id:
            filters.append(TimesheetPeriodORM.resource_id == criteria.resource_id)
        if criteria.period_start_from is not None:
            filters.append(TimesheetPeriodORM.period_start >= criteria.period_start_from)
        if criteria.period_start_to is not None:
            filters.append(TimesheetPeriodORM.period_start <= criteria.period_start_to)
        if allowed_project_ids is not None:
            filters.append(project_id.in_(allowed_project_ids))

        def joined(stmt):
            return (
                stmt.join(ResourceORM, ResourceORM.id == TimesheetPeriodORM.resource_id)
                .join(
                    TaskAssignmentORM,
                    TaskAssignmentORM.resource_id == TimesheetPeriodORM.resource_id,
                )
                .join(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
                .join(TimeEntryORM, allocation_id == TaskAssignmentORM.id)
                .join(ProjectORM, ProjectORM.id == project_id)
                .where(
                    TimeEntryORM.entry_date >= TimesheetPeriodORM.period_start,
                    TimeEntryORM.entry_date <= TimesheetPeriodORM.period_end,
                    *filters,
                )
            )

        match_filters = []
        if criteria.project_id:
            match_filters.append(project_id == criteria.project_id)
        if criteria.search_text:
            escaped = (
                criteria.search_text.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            pattern = f"%{escaped.lower()}%"
            match_filters.append(
                or_(
                    func.lower(ResourceORM.name).like(pattern, escape="\\"),
                    func.lower(ProjectORM.name).like(pattern, escape="\\"),
                    func.lower(TaskORM.name).like(pattern, escape="\\"),
                    func.lower(func.coalesce(TimeEntryORM.note, "")).like(pattern, escape="\\"),
                    func.lower(func.coalesce(TimesheetPeriodORM.submitted_by_username, "")).like(
                        pattern, escape="\\"
                    ),
                )
            )

        period_ids = joined(
            select(TimesheetPeriodORM.id.label("period_id"))
            .select_from(TimesheetPeriodORM)
        ).where(*match_filters).group_by(TimesheetPeriodORM.id).subquery()
        total = int(self._session.scalar(select(func.count()).select_from(period_ids)) or 0)
        selected_period_ids = select(period_ids.c.period_id)

        summary_stmt = joined(
            select(
                TimesheetPeriodORM.id,
                TimesheetPeriodORM.resource_id,
                ResourceORM.name,
                TimesheetPeriodORM.period_start,
                TimesheetPeriodORM.period_end,
                TimesheetPeriodORM.status,
                TimesheetPeriodORM.submitted_at,
                TimesheetPeriodORM.submitted_by_username,
                TimesheetPeriodORM.decided_at,
                TimesheetPeriodORM.decided_by_username,
                TimesheetPeriodORM.decision_note,
                func.count(func.distinct(TimeEntryORM.id)),
                func.sum(TimeEntryORM.hours),
            ).select_from(TimesheetPeriodORM)
        ).where(TimesheetPeriodORM.id.in_(selected_period_ids)).group_by(
            TimesheetPeriodORM.id,
            TimesheetPeriodORM.resource_id,
            ResourceORM.name,
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
            "title": (func.lower(ResourceORM.name), TimesheetPeriodORM.period_start),
            "statusLabel": (TimesheetPeriodORM.status,),
            "supportingText": (func.sum(TimeEntryORM.hours),),
            "metaText": (TimesheetPeriodORM.submitted_at,),
            "submittedAt": (
                TimesheetPeriodORM.submitted_at,
                TimesheetPeriodORM.period_start,
            ),
        }
        summary_rows = self._session.execute(
            summary_stmt
            .order_by(*stable_order_by(
                sort=criteria.sort,
                expressions=sort_expressions,
                default_key="submittedAt",
                tie_breakers=(TimesheetPeriodORM.id,),
            ))
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
                    ).select_from(TimesheetPeriodORM)
                )
                .where(TimesheetPeriodORM.id.in_(page_period_ids))
                .distinct()
            ).all()
            for period_id_value, project_id_value in project_rows:
                projects_by_period[str(period_id_value)].add(str(project_id_value))

        return TimesheetReviewReadPage(
            items=tuple(
                TimesheetReviewQueueItem(
                    period_id=str(row[0]),
                    resource_id=str(row[1]),
                    resource_name=str(row[2] or row[1]),
                    period_start=row[3],
                    period_end=row[4],
                    status=row[5],
                    submitted_at=row[6],
                    submitted_by_username=row[7],
                    decided_at=row[8],
                    decided_by_username=row[9],
                    decision_note=row[10],
                    entry_count=int(row[11] or 0),
                    total_hours=float(row[12] or 0.0),
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
