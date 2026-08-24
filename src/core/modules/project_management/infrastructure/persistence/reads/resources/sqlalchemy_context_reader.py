from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from sqlalchemy import and_, case, false, func, or_, select
from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.reads.resources import (
    ResourceActivityFact,
    ResourceActivityReadPage,
    ResourceAssignmentFact,
    ResourceAssignmentReadPage,
    ResourceProjectFact,
    ResourceProjectReadPage,
)
from src.core.modules.project_management.contracts.reads.sorting import (
    ReadSort,
    ReadSortDirection,
)
from src.core.modules.project_management.domain.enums import ProjectStatus, TaskStatus
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
    ProjectResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskORM,
)
from src.core.modules.project_management.infrastructure.persistence.reads.sorting import (
    stable_order_by,
)
from src.core.platform.infrastructure.persistence.orm.history.activity.activity import (
    ActivityEntryORM,
)
from src.core.platform.infrastructure.persistence.orm.time_management.time.time import (
    TimeEntryORM,
)


def _contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped.lower()}%"


def _json_field_pattern(field: str, value: str) -> str:
    marker = json.dumps({field: value}, ensure_ascii=False)[1:-1]
    return _contains_pattern(marker)


def _scoped_resource_filter(*, tenant_id: str, organization_id: str, resource_id: str):
    return (
        ResourceORM.id == resource_id,
        ResourceORM.tenant_id == tenant_id,
        ResourceORM.organization_id == organization_id,
    )


def _allowed_projects_filter(allowed_project_ids: tuple[str, ...] | None):
    if allowed_project_ids is None:
        return None
    if not allowed_project_ids:
        return false()
    return ProjectORM.id.in_(allowed_project_ids)


def _enum_value(value: object) -> str:
    return str(getattr(value, "value", value) or "")


def _activity_category(action: str) -> str:
    normalized = str(action or "").lower()
    if normalized.startswith("resource.skill") or normalized.startswith(
        "resource.certification"
    ):
        return "capability"
    if normalized.startswith("project_resource"):
        return "projects"
    if normalized.startswith("assignment"):
        return "assignments"
    if normalized.startswith("time") or normalized.startswith("timesheet"):
        return "work"
    return "resource"


class SqlAlchemyResourceContextReader:
    """Bounded Resource-centric projections over separately owned PM facts."""

    def __init__(self, *, session: Session) -> None:
        self._session = session

    def read_projects_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        resource_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        search_text: str,
        active: bool | None,
        status: ProjectStatus | None,
        page: int,
        page_size: int,
        sort: ReadSort,
    ) -> ResourceProjectReadPage:
        filters = [
            *_scoped_resource_filter(
                tenant_id=tenant_id,
                organization_id=organization_id,
                resource_id=resource_id,
            ),
            ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
        ]
        allowed_filter = _allowed_projects_filter(allowed_project_ids)
        if allowed_filter is not None:
            filters.append(allowed_filter)
        if active is not None:
            filters.append(ProjectResourceORM.is_active.is_(active))
        if status is not None:
            filters.append(ProjectORM.status == status)
        normalized_search = str(search_text or "").strip()
        if normalized_search:
            pattern = _contains_pattern(normalized_search)
            filters.append(
                or_(
                    func.lower(ProjectORM.name).like(pattern, escape="\\"),
                    func.lower(func.coalesce(ProjectORM.project_code, "")).like(
                        pattern, escape="\\"
                    ),
                )
            )

        base = (
            select(ProjectResourceORM.id)
            .select_from(ProjectResourceORM)
            .join(ResourceORM, ResourceORM.id == ProjectResourceORM.resource_id)
            .join(ProjectORM, ProjectORM.id == ProjectResourceORM.project_id)
            .where(*filters)
        )
        filtered_total = int(
            self._session.scalar(select(func.count()).select_from(base.subquery())) or 0
        )
        sort_expressions = {
            "projectName": (func.lower(ProjectORM.name),),
            "projectCode": (func.lower(func.coalesce(ProjectORM.project_code, "")),),
            "statusLabel": (ProjectORM.status,),
            "plannedHours": (ProjectResourceORM.planned_hours,),
            "startDate": (ProjectORM.start_date,),
            "endDate": (ProjectORM.end_date,),
        }
        order_by = stable_order_by(
            sort=sort,
            expressions=sort_expressions,
            default_key="projectName",
            tie_breakers=(ProjectResourceORM.id,),
        )
        rows = self._session.execute(
            select(
                ProjectResourceORM.id,
                ProjectResourceORM.resource_id,
                ProjectORM.id,
                ProjectORM.project_code,
                ProjectORM.name,
                ProjectORM.status,
                ProjectResourceORM.planned_hours,
                ProjectResourceORM.is_active,
                ProjectORM.start_date,
                ProjectORM.end_date,
                ProjectResourceORM.version,
            )
            .select_from(ProjectResourceORM)
            .join(ResourceORM, ResourceORM.id == ProjectResourceORM.resource_id)
            .join(ProjectORM, ProjectORM.id == ProjectResourceORM.project_id)
            .where(*filters)
            .order_by(*order_by)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return ResourceProjectReadPage(
            items=tuple(
                ResourceProjectFact(
                    project_resource_id=str(row[0]),
                    resource_id=str(row[1]),
                    project_id=str(row[2]),
                    project_code=str(row[3] or ""),
                    project_name=str(row[4] or ""),
                    project_status=_enum_value(row[5]),
                    planned_hours=Decimal(str(row[6] or 0)),
                    is_active=bool(row[7]),
                    start_date=row[8],
                    end_date=row[9],
                    version=int(row[10] or 1),
                )
                for row in rows
            ),
            filtered_total=filtered_total,
            page=page,
            page_size=page_size,
            sort=sort,
        )

    def read_assignments_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        resource_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        search_text: str,
        project_id: str | None,
        task_status: TaskStatus | None,
        assignment_status: str | None,
        lifecycle: str,
        start_date: date | None,
        end_date: date | None,
        page: int,
        page_size: int,
        sort: ReadSort,
    ) -> ResourceAssignmentReadPage:
        actuals = (
            select(
                TimeEntryORM.assignment_id.label("assignment_id"),
                func.count(TimeEntryORM.id).label("entry_count"),
                func.coalesce(func.sum(TimeEntryORM.hours), 0).label("actual_hours"),
            )
            .where(
                TimeEntryORM.tenant_id == tenant_id,
                TimeEntryORM.organization_id == organization_id,
                TimeEntryORM.assignment_id.is_not(None),
            )
            .group_by(TimeEntryORM.assignment_id)
            .subquery()
        )
        actual_hours = case(
            (func.coalesce(actuals.c.entry_count, 0) > 0, actuals.c.actual_hours),
            else_=TaskAssignmentORM.hours_logged,
        )
        filters = [
            *_scoped_resource_filter(
                tenant_id=tenant_id,
                organization_id=organization_id,
                resource_id=resource_id,
            ),
            ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
        ]
        allowed_filter = _allowed_projects_filter(allowed_project_ids)
        if allowed_filter is not None:
            filters.append(allowed_filter)
        if project_id:
            filters.append(ProjectORM.id == project_id)
        if task_status is not None:
            filters.append(TaskORM.status == task_status)
        if assignment_status:
            filters.append(func.lower(TaskAssignmentORM.response_status) == assignment_status)
        if lifecycle == "current":
            filters.append(TaskORM.status != TaskStatus.DONE)
        elif lifecycle == "history":
            filters.append(TaskORM.status == TaskStatus.DONE)
        if start_date is not None:
            filters.append(or_(TaskORM.end_date.is_(None), TaskORM.end_date >= start_date))
        if end_date is not None:
            filters.append(or_(TaskORM.start_date.is_(None), TaskORM.start_date <= end_date))
        normalized_search = str(search_text or "").strip()
        if normalized_search:
            pattern = _contains_pattern(normalized_search)
            filters.append(
                or_(
                    func.lower(TaskORM.name).like(pattern, escape="\\"),
                    func.lower(func.coalesce(TaskORM.task_code, "")).like(
                        pattern, escape="\\"
                    ),
                    func.lower(ProjectORM.name).like(pattern, escape="\\"),
                    func.lower(func.coalesce(ProjectORM.project_code, "")).like(
                        pattern, escape="\\"
                    ),
                )
            )

        from_clause = (
            TaskAssignmentORM.__table__
            .join(ResourceORM, ResourceORM.id == TaskAssignmentORM.resource_id)
            .join(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
            .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .outerjoin(actuals, actuals.c.assignment_id == TaskAssignmentORM.id)
        )
        filtered_total = int(
            self._session.scalar(
                select(func.count(TaskAssignmentORM.id))
                .select_from(from_clause)
                .where(*filters)
            )
            or 0
        )
        sort_expressions = {
            "projectName": (func.lower(ProjectORM.name),),
            "taskName": (func.lower(TaskORM.name),),
            "scheduledStart": (TaskORM.start_date,),
            "scheduledFinish": (TaskORM.end_date,),
            "plannedHours": (TaskAssignmentORM.allocated_planned_hours,),
            "allocationPercent": (TaskAssignmentORM.allocation_percent,),
            "actualHours": (actual_hours,),
            "statusLabel": (TaskORM.status,),
        }
        order_by = stable_order_by(
            sort=sort,
            expressions=sort_expressions,
            default_key="scheduledStart",
            tie_breakers=(TaskAssignmentORM.id,),
        )
        rows = self._session.execute(
            select(
                TaskAssignmentORM.id,
                TaskAssignmentORM.resource_id,
                ProjectORM.id,
                ProjectORM.project_code,
                ProjectORM.name,
                TaskORM.id,
                TaskORM.task_code,
                TaskORM.name,
                TaskORM.status,
                TaskORM.start_date,
                TaskORM.end_date,
                TaskAssignmentORM.allocated_planned_hours,
                TaskAssignmentORM.allocation_percent,
                actual_hours,
                func.coalesce(actuals.c.entry_count, 0),
                TaskAssignmentORM.response_status,
                TaskAssignmentORM.project_resource_id,
                TaskAssignmentORM.version,
            )
            .select_from(from_clause)
            .where(*filters)
            .order_by(*order_by)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return ResourceAssignmentReadPage(
            items=tuple(
                ResourceAssignmentFact(
                    assignment_id=str(row[0]),
                    resource_id=str(row[1]),
                    project_id=str(row[2]),
                    project_code=str(row[3] or ""),
                    project_name=str(row[4] or ""),
                    task_id=str(row[5]),
                    task_code=str(row[6] or ""),
                    task_name=str(row[7] or ""),
                    task_status=_enum_value(row[8]),
                    scheduled_start=row[9],
                    scheduled_finish=row[10],
                    allocated_planned_hours=Decimal(str(row[11] or 0)),
                    allocation_percent=Decimal(str(row[12] or 0)),
                    actual_hours=Decimal(str(row[13] or 0)),
                    actual_hours_source=(
                        "time_entries" if int(row[14] or 0) > 0 else "synchronized_assignment"
                    ),
                    response_status=str(row[15] or "pending"),
                    project_resource_id=str(row[16]) if row[16] else None,
                    assignment_version=int(row[17] or 1),
                )
                for row in rows
            ),
            filtered_total=filtered_total,
            page=page,
            page_size=page_size,
            sort=sort,
        )

    def read_activity_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        resource_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        allowed_task_project_ids: tuple[str, ...] | None,
        category: str,
        start_date: date | None,
        end_date: date | None,
        page: int,
        page_size: int,
    ) -> ResourceActivityReadPage:
        resource_exists = select(ResourceORM.id).where(
            *_scoped_resource_filter(
                tenant_id=tenant_id,
                organization_id=organization_id,
                resource_id=resource_id,
            )
        ).exists()
        direct_resource = and_(
            ActivityEntryORM.entity_type == "resource",
            ActivityEntryORM.entity_id == resource_id,
        )
        marker = _json_field_pattern("resource_id", resource_id)
        project_staffing = and_(
            ActivityEntryORM.entity_type == "project_resource",
            func.lower(ActivityEntryORM.details_json).like(marker, escape="\\"),
        )
        assignment_staffing = and_(
            ActivityEntryORM.entity_type == "task_assignment",
            func.lower(ActivityEntryORM.details_json).like(marker, escape="\\"),
        )
        if allowed_project_ids is not None:
            project_staffing = and_(
                project_staffing,
                ActivityEntryORM.workspace_id.in_(allowed_project_ids)
                if allowed_project_ids
                else false(),
            )
        if allowed_task_project_ids is not None:
            assignment_staffing = and_(
                assignment_staffing,
                ActivityEntryORM.workspace_id.in_(allowed_task_project_ids)
                if allowed_task_project_ids
                else false(),
            )
        staffing = or_(project_staffing, assignment_staffing)
        filters = [
            resource_exists,
            ActivityEntryORM.tenant_id == tenant_id,
            ActivityEntryORM.organization_id == organization_id,
            ActivityEntryORM.module == "project_management",
            or_(direct_resource, staffing),
        ]
        normalized_category = str(category or "all").strip().lower()
        if normalized_category == "resource":
            filters.append(
                ActivityEntryORM.action.in_(
                    (
                        "resource.created",
                        "resource.updated",
                        "resource.deactivated",
                        "resource.reactivated",
                        "resource.purged",
                    )
                )
            )
        elif normalized_category == "capability":
            filters.append(
                or_(
                    ActivityEntryORM.action.startswith("resource.skill"),
                    ActivityEntryORM.action.startswith("resource.certification"),
                )
            )
        elif normalized_category == "projects":
            filters.append(ActivityEntryORM.action.startswith("project_resource"))
        elif normalized_category == "assignments":
            filters.append(ActivityEntryORM.action.startswith("assignment"))
        elif normalized_category == "work":
            filters.append(
                or_(
                    ActivityEntryORM.action.startswith("time"),
                    ActivityEntryORM.action.startswith("timesheet"),
                )
            )
        if start_date is not None:
            filters.append(func.date(ActivityEntryORM.timestamp) >= start_date)
        if end_date is not None:
            filters.append(func.date(ActivityEntryORM.timestamp) <= end_date)

        filtered_total = int(
            self._session.scalar(
                select(func.count(ActivityEntryORM.id)).where(*filters)
            )
            or 0
        )
        rows = self._session.execute(
            select(
                ActivityEntryORM.id,
                ActivityEntryORM.timestamp,
                ActivityEntryORM.action,
                ActivityEntryORM.actor_id,
                ActivityEntryORM.human_message,
                ActivityEntryORM.entity_type,
                ActivityEntryORM.entity_id,
                ActivityEntryORM.workspace_id,
                ActivityEntryORM.parent_entity_id,
            )
            .where(*filters)
            .order_by(ActivityEntryORM.timestamp.desc(), ActivityEntryORM.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        facts: list[ResourceActivityFact] = []
        for row in rows:
            category_value = _activity_category(str(row[2] or ""))
            project_id = str(row[7]) if row[7] and category_value in {"projects", "assignments"} else None
            task_id = str(row[8]) if row[8] and category_value == "assignments" else None
            source_type = "task" if task_id else "project" if project_id else "resource"
            source_id = task_id or project_id or resource_id
            facts.append(
                ResourceActivityFact(
                    activity_id=str(row[0]),
                    resource_id=resource_id,
                    occurred_at=row[1],
                    event_type=str(row[2] or "activity"),
                    category=category_value,
                    actor_label="System" if not row[3] else "Authorized user",
                    summary=str(row[4] or row[2] or "Activity recorded"),
                    source_type=source_type,
                    source_id=source_id,
                    project_id=project_id,
                    task_id=task_id,
                    can_open_source=bool(project_id or task_id),
                )
            )
        return ResourceActivityReadPage(
            items=tuple(facts),
            filtered_total=filtered_total,
            page=page,
            page_size=page_size,
            sort=ReadSort("occurredAt", ReadSortDirection.DESCENDING),
        )


__all__ = ["SqlAlchemyResourceContextReader"]
