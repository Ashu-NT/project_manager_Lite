from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import String, and_, case, cast, false, func, or_, select
from sqlalchemy.orm import Session, aliased
from src.core.modules.project_management.contracts.reads.sorting import ReadSort
from src.core.modules.project_management.infrastructure.persistence.reads.sorting import stable_order_by

from src.core.modules.project_management.contracts.reads.tasks import (
    TaskWorkspaceCriteria,
    TaskActivityFact,
    TaskActivityPage,
    TaskAssignmentReadItem,
    TaskAssignmentReadPage,
    TaskDependencyReadItem,
    TaskDependencyReadPage,
    TaskWorkspaceReadItem,
    TaskWorkspaceReadPage,
    TaskWorkspaceSummary,
)
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskDependencyORM,
    TaskORM,
)
from src.core.platform.infrastructure.persistence.orm.history.activity.activity import ActivityEntryORM
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import EmployeeORM
from src.core.platform.infrastructure.persistence.orm.time_management.time.time import TimeEntryORM


def _contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped.lower()}%"


def _compare(column, operator: str, value):
    resolved = "=" if operator == ":" else operator
    if resolved == "=":
        return column == value
    if resolved == ">=":
        return column >= value
    if resolved == "<=":
        return column <= value
    if resolved == ">":
        return column > value
    if resolved == "<":
        return column < value
    return false()


class SqlAlchemyTaskWorkspaceReader:
    def __init__(self, *, session: Session) -> None:
        self._session = session

    def read_assignments_page(
        self, *, tenant_id: str, organization_id: str, task_id: str,
        search_text: str, response_status: str | None, page: int,
        page_size: int, sort: ReadSort,
    ) -> TaskAssignmentReadPage:
        time_actuals = (
            select(
                TimeEntryORM.assignment_id.label("assignment_id"),
                func.count(TimeEntryORM.id).label("entry_count"),
                func.coalesce(func.sum(TimeEntryORM.hours), 0).label("hours"),
            )
            .where(
                TimeEntryORM.tenant_id == tenant_id,
                TimeEntryORM.organization_id == organization_id,
                TimeEntryORM.assignment_id.is_not(None),
            )
            .group_by(TimeEntryORM.assignment_id)
            .subquery("task_detail_time_actuals")
        )
        actual = case(
            (func.coalesce(time_actuals.c.entry_count, 0) > 0, time_actuals.c.hours),
            else_=TaskAssignmentORM.hours_logged,
        )
        filters = [
            TaskAssignmentORM.task_id == task_id,
            ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
            ResourceORM.tenant_id == tenant_id,
            ResourceORM.organization_id == organization_id,
        ]
        if response_status:
            filters.append(func.lower(TaskAssignmentORM.response_status) == response_status)
        normalized_search = str(search_text or "").strip()
        if normalized_search:
            pattern = _contains_pattern(normalized_search)
            filters.append(or_(
                func.lower(ResourceORM.name).like(pattern, escape="\\"),
                func.lower(func.coalesce(ResourceORM.resource_code, "")).like(pattern, escape="\\"),
                func.lower(func.coalesce(ResourceORM.role, "")).like(pattern, escape="\\"),
            ))
        from_clause = (
            TaskAssignmentORM.__table__
            .join(TaskORM, TaskORM.id == TaskAssignmentORM.task_id)
            .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .join(ResourceORM, ResourceORM.id == TaskAssignmentORM.resource_id)
            .outerjoin(
                EmployeeORM,
                and_(
                    EmployeeORM.id == ResourceORM.employee_id,
                    EmployeeORM.tenant_id == tenant_id,
                    EmployeeORM.organization_id == organization_id,
                ),
            )
            .outerjoin(time_actuals, time_actuals.c.assignment_id == TaskAssignmentORM.id)
        )
        total = int(self._session.scalar(
            select(func.count(TaskAssignmentORM.id)).select_from(from_clause).where(*filters)
        ) or 0)
        sort_expressions = {
            "resourceName": (func.lower(ResourceORM.name),),
            "resourceCode": (func.lower(func.coalesce(ResourceORM.resource_code, "")),),
            "role": (func.lower(func.coalesce(ResourceORM.role, "")),),
            "allocationPercent": (TaskAssignmentORM.allocation_percent,),
            "plannedHours": (TaskAssignmentORM.allocated_planned_hours,),
            "actualHours": (actual,),
            "remainingHours": (TaskAssignmentORM.allocated_planned_hours - actual,),
            "responseStatus": (func.lower(TaskAssignmentORM.response_status),),
        }
        rows = self._session.execute(select(
            TaskAssignmentORM.id, ResourceORM.id, ResourceORM.resource_code,
            ResourceORM.name, ResourceORM.role, TaskAssignmentORM.allocation_percent,
            TaskAssignmentORM.allocated_planned_hours, actual,
            TaskAssignmentORM.response_status, TaskAssignmentORM.project_resource_id,
            TaskAssignmentORM.version, EmployeeORM.user_id,
        ).select_from(from_clause).where(*filters).order_by(*stable_order_by(
            sort=sort, expressions=sort_expressions, default_key="resourceName",
            tie_breakers=(TaskAssignmentORM.id,),
        )).offset((page - 1) * page_size).limit(page_size)).all()
        return TaskAssignmentReadPage(items=tuple(TaskAssignmentReadItem(
            assignment_id=str(r[0]), resource_id=str(r[1]), resource_code=str(r[2] or ""),
            resource_name=str(r[3] or ""), role=str(r[4] or ""),
            allocation_percent=Decimal(str(r[5] or 0)), planned_hours=Decimal(str(r[6] or 0)),
            actual_hours=Decimal(str(r[7] or 0)), response_status=str(r[8] or "pending"),
            project_resource_id=str(r[9]) if r[9] else None, version=int(r[10] or 1),
            assignee_user_id=str(r[11]) if r[11] else None,
        ) for r in rows), filtered_total=total, page=page, page_size=page_size, sort=sort)

    def read_dependencies_page(
        self, *, tenant_id: str, organization_id: str, task_id: str,
        search_text: str, direction: str, dependency_type: str | None,
        page: int, page_size: int, sort: ReadSort,
    ) -> TaskDependencyReadPage:
        current = aliased(TaskORM, name="dependency_current_task")
        linked = aliased(TaskORM, name="dependency_linked_task")
        direction_expr = case(
            (TaskDependencyORM.successor_task_id == task_id, "PREDECESSOR"),
            else_="SUCCESSOR",
        )
        linked_id = case(
            (TaskDependencyORM.successor_task_id == task_id, TaskDependencyORM.predecessor_task_id),
            else_=TaskDependencyORM.successor_task_id,
        )
        filters = [
            or_(TaskDependencyORM.predecessor_task_id == task_id, TaskDependencyORM.successor_task_id == task_id),
            current.id == task_id,
            ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
        ]
        normalized_direction = str(direction or "all").upper()
        if normalized_direction in {"PREDECESSOR", "SUCCESSOR"}:
            filters.append(direction_expr == normalized_direction)
        if dependency_type:
            filters.append(cast(TaskDependencyORM.dependency_type, String) == dependency_type)
        normalized_search = str(search_text or "").strip()
        if normalized_search:
            pattern = _contains_pattern(normalized_search)
            filters.append(or_(
                func.lower(linked.name).like(pattern, escape="\\"),
                func.lower(func.coalesce(linked.task_code, "")).like(pattern, escape="\\"),
                func.lower(linked.wbs_code).like(pattern, escape="\\"),
            ))
        from_clause = (
            TaskDependencyORM.__table__
            .join(current, or_(current.id == TaskDependencyORM.predecessor_task_id, current.id == TaskDependencyORM.successor_task_id))
            .join(ProjectORM, ProjectORM.id == current.project_id)
            .join(linked, linked.id == linked_id)
        )
        base_filters = filters[:4]
        predecessor_total = int(self._session.scalar(select(func.count(TaskDependencyORM.id)).select_from(from_clause).where(*base_filters, direction_expr == "PREDECESSOR")) or 0)
        successor_total = int(self._session.scalar(select(func.count(TaskDependencyORM.id)).select_from(from_clause).where(*base_filters, direction_expr == "SUCCESSOR")) or 0)
        total = int(self._session.scalar(select(func.count(TaskDependencyORM.id)).select_from(from_clause).where(*filters)) or 0)
        sort_expressions = {
            "direction": (direction_expr,), "linkedTask": (func.lower(linked.name),),
            "taskCode": (func.lower(func.coalesce(linked.task_code, "")),),
            "dependencyType": (TaskDependencyORM.dependency_type,), "lagDays": (TaskDependencyORM.lag_days,),
            "startDate": (linked.start_date,), "endDate": (linked.end_date,), "statusLabel": (linked.status,),
        }
        rows = self._session.execute(select(
            TaskDependencyORM.id, direction_expr, linked.id, linked.task_code,
            linked.name, linked.status, linked.start_date, linked.end_date,
            TaskDependencyORM.dependency_type, TaskDependencyORM.lag_days, TaskDependencyORM.version,
        ).select_from(from_clause).where(*filters).order_by(*stable_order_by(
            sort=sort, expressions=sort_expressions, default_key="linkedTask",
            tie_breakers=(TaskDependencyORM.id,),
        )).offset((page - 1) * page_size).limit(page_size)).all()
        return TaskDependencyReadPage(items=tuple(TaskDependencyReadItem(
            dependency_id=str(r[0]), direction=str(r[1]), linked_task_id=str(r[2]),
            linked_task_code=str(r[3] or ""), linked_task_name=str(r[4] or ""),
            linked_task_status=str(getattr(r[5], "value", r[5]) or "TODO"),
            linked_task_start=r[6], linked_task_end=r[7],
            dependency_type=str(getattr(r[8], "value", r[8]) or "FINISH_TO_START"),
            lag_days=int(r[9] or 0), version=int(r[10] or 1),
        ) for r in rows), filtered_total=total, predecessor_total=predecessor_total,
            successor_total=successor_total, page=page, page_size=page_size, sort=sort)

    def read_activity_page(
        self, *, tenant_id: str, organization_id: str, task_id: str,
        search_text: str, category: str, page: int, page_size: int,
    ) -> TaskActivityPage:
        task_exists = select(TaskORM.id).join(ProjectORM, ProjectORM.id == TaskORM.project_id).where(
            TaskORM.id == task_id, ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
        ).exists()
        primary = and_(ActivityEntryORM.entity_type == "task", ActivityEntryORM.entity_id == task_id)
        assignments = and_(ActivityEntryORM.entity_type == "task_assignment", ActivityEntryORM.parent_entity_id == task_id)
        filters = [task_exists, ActivityEntryORM.tenant_id == tenant_id,
                   ActivityEntryORM.organization_id == organization_id,
                   ActivityEntryORM.module == "project_management", or_(primary, assignments)]
        normalized_category = str(category or "all").lower()
        if normalized_category == "task": filters.append(primary)
        elif normalized_category == "assignments": filters.append(assignments)
        normalized_search = str(search_text or "").strip()
        if normalized_search:
            pattern = _contains_pattern(normalized_search)
            filters.append(or_(func.lower(ActivityEntryORM.action).like(pattern, escape="\\"),
                               func.lower(func.coalesce(ActivityEntryORM.human_message, "")).like(pattern, escape="\\")))
        total = int(self._session.scalar(select(func.count(ActivityEntryORM.id)).where(*filters)) or 0)
        rows = self._session.execute(select(
            ActivityEntryORM.id, ActivityEntryORM.timestamp, ActivityEntryORM.actor_id,
            ActivityEntryORM.action, ActivityEntryORM.entity_type,
            ActivityEntryORM.human_message, ActivityEntryORM.details,
        ).where(*filters).order_by(ActivityEntryORM.timestamp.desc(), ActivityEntryORM.id.desc())
          .offset((page - 1) * page_size).limit(page_size)).all()
        activity_sort = ReadSort.normalize(key="occurredAt", direction="desc", allowed_keys={"occurredAt"}, default_key="occurredAt")
        return TaskActivityPage(items=tuple(TaskActivityFact(
            activity_id=str(r[0]), occurred_at=r[1], actor_id=str(r[2]) if r[2] else None,
            action=str(r[3] or "activity"), entity_type=str(r[4] or "task"),
            summary=str(r[5] or r[3] or "Activity recorded"), details=dict(r[6] or {}),
        ) for r in rows), filtered_total=total, page=page, page_size=page_size, sort=activity_sort)

    def _effective_rows(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
    ):
        scope_filters = [
            ProjectORM.tenant_id == tenant_id,
            ProjectORM.organization_id == organization_id,
        ]
        if allowed_project_ids is not None:
            scope_filters.append(ProjectORM.id.in_(allowed_project_ids))

        closure = (
            select(
                TaskORM.id.label("root_id"),
                TaskORM.id.label("descendant_id"),
                TaskORM.project_id.label("project_id"),
            )
            .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .where(*scope_filters)
            .cte("task_workspace_closure", recursive=True)
        )
        child = aliased(TaskORM)
        closure = closure.union_all(
            select(
                closure.c.root_id,
                child.id,
                closure.c.project_id,
            ).where(
                child.project_id == closure.c.project_id,
                child.parent_task_id == closure.c.descendant_id,
            )
        )

        child_counts = (
            select(
                TaskORM.parent_task_id.label("task_id"),
                func.count(TaskORM.id).label("child_count"),
            )
            .where(TaskORM.parent_task_id.is_not(None))
            .group_by(TaskORM.parent_task_id)
            .subquery("task_workspace_child_counts")
        )
        descendant = aliased(TaskORM)
        descendant_child_counts = child_counts.alias("descendant_child_counts")
        weight = func.coalesce(descendant.duration_days, 0)
        rollups = (
            select(
                closure.c.root_id,
                func.min(descendant.start_date).label("rollup_start_date"),
                func.max(descendant.end_date).label("rollup_end_date"),
                func.sum(weight).label("rollup_duration_days"),
                func.sum(descendant.percent_complete * weight).label("weighted_progress"),
                func.sum(weight).label("progress_weight"),
                func.avg(descendant.percent_complete).label("average_progress"),
                func.count(descendant.id).label("leaf_count"),
                func.sum(case((descendant.status == TaskStatus.DONE, 1), else_=0)).label(
                    "done_count"
                ),
                func.sum(case((descendant.status == TaskStatus.BLOCKED, 1), else_=0)).label(
                    "blocked_count"
                ),
                func.sum(
                    case(
                        (
                            (descendant.status == TaskStatus.IN_PROGRESS)
                            | (descendant.percent_complete > 0),
                            1,
                        ),
                        else_=0,
                    )
                ).label("started_count"),
            )
            .join(descendant, descendant.id == closure.c.descendant_id)
            .outerjoin(
                descendant_child_counts,
                descendant_child_counts.c.task_id == descendant.id,
            )
            .where(func.coalesce(descendant_child_counts.c.child_count, 0) == 0)
            .group_by(closure.c.root_id)
            .subquery("task_workspace_rollups")
        )
        depths = (
            select(
                closure.c.descendant_id.label("task_id"),
                (func.count(closure.c.root_id) - 1).label("hierarchy_depth"),
            )
            .group_by(closure.c.descendant_id)
            .subquery("task_workspace_depths")
        )

        direct_child_count = func.coalesce(child_counts.c.child_count, 0)
        is_summary = direct_child_count > 0
        summary_status = case(
            (rollups.c.done_count == rollups.c.leaf_count, TaskStatus.DONE.value),
            (rollups.c.blocked_count > 0, TaskStatus.BLOCKED.value),
            (rollups.c.started_count > 0, TaskStatus.IN_PROGRESS.value),
            else_=TaskStatus.TODO.value,
        )
        effective_status = case(
            (is_summary, summary_status),
            else_=cast(TaskORM.status, String),
        )
        effective_progress = case(
            (
                is_summary,
                case(
                    (
                        rollups.c.progress_weight > 0,
                        rollups.c.weighted_progress / rollups.c.progress_weight,
                    ),
                    else_=func.coalesce(rollups.c.average_progress, 0.0),
                ),
            ),
            else_=TaskORM.percent_complete,
        )

        return (
            select(
                TaskORM.id.label("id"),
                TaskORM.project_id.label("project_id"),
                ProjectORM.name.label("project_name"),
                TaskORM.name.label("name"),
                TaskORM.task_code.label("code"),
                TaskORM.description.label("description"),
                effective_status.label("status"),
                case((is_summary, rollups.c.rollup_start_date), else_=TaskORM.start_date).label(
                    "start_date"
                ),
                case((is_summary, rollups.c.rollup_end_date), else_=TaskORM.end_date).label(
                    "end_date"
                ),
                case(
                    (is_summary, rollups.c.rollup_duration_days),
                    else_=TaskORM.duration_days,
                ).label("duration_days"),
                TaskORM.priority.label("priority"),
                effective_progress.label("percent_complete"),
                TaskORM.actual_start.label("actual_start"),
                TaskORM.actual_end.label("actual_end"),
                TaskORM.deadline.label("deadline"),
                TaskORM.version.label("version"),
                TaskORM.parent_task_id.label("parent_task_id"),
                TaskORM.wbs_code.label("wbs_code"),
                TaskORM.sort_order.label("sort_order"),
                is_summary.label("is_summary"),
                func.coalesce(depths.c.hierarchy_depth, 0).label("hierarchy_depth"),
                direct_child_count.label("child_count"),
                TaskORM.is_milestone.label("is_milestone"),
            )
            .join(ProjectORM, ProjectORM.id == TaskORM.project_id)
            .outerjoin(child_counts, child_counts.c.task_id == TaskORM.id)
            .outerjoin(rollups, rollups.c.root_id == TaskORM.id)
            .outerjoin(depths, depths.c.task_id == TaskORM.id)
            .where(*scope_filters)
            .subquery("task_workspace_effective_rows")
        )

    @staticmethod
    def _filtered_conditions(rows, criteria: TaskWorkspaceCriteria) -> list:
        conditions = []
        if criteria.project_id:
            conditions.append(rows.c.project_id == criteria.project_id)
        if criteria.status != "ALL":
            conditions.append(rows.c.status == criteria.status)
        if criteria.priority == "high":
            conditions.append(rows.c.priority >= 70)
        elif criteria.priority == "medium":
            conditions.extend((rows.c.priority >= 30, rows.c.priority <= 69))
        elif criteria.priority == "low":
            conditions.append(rows.c.priority < 30)

        current_date = criteria.as_of or date.today()
        if criteria.schedule == "overdue":
            conditions.extend((rows.c.deadline.is_not(None), rows.c.deadline < current_date))
        elif criteria.schedule == "due_7":
            conditions.extend(
                (
                    rows.c.deadline.is_not(None),
                    rows.c.deadline >= current_date,
                    rows.c.deadline <= current_date + timedelta(days=7),
                )
            )
        elif criteria.schedule == "no_deadline":
            conditions.append(rows.c.deadline.is_(None))

        if criteria.milestones_only:
            conditions.append(rows.c.is_milestone.is_(True))

        for term in criteria.search_terms:
            pattern = _contains_pattern(term)
            conditions.append(
                or_(
                    func.lower(rows.c.name).like(pattern, escape="\\"),
                    func.lower(func.coalesce(rows.c.description, "")).like(pattern, escape="\\"),
                    func.lower(rows.c.project_name).like(pattern, escape="\\"),
                )
            )
        for condition in criteria.conditions:
            field = condition.field
            if field == "status":
                if condition.operator in {":", "="}:
                    conditions.append(rows.c.status == condition.value.upper())
                continue
            if field in {"priority", "progress"}:
                try:
                    expected_number = float(condition.value)
                except ValueError:
                    conditions.append(false())
                    continue
                column = rows.c.priority if field == "priority" else rows.c.percent_complete
                conditions.append(_compare(column, condition.operator, expected_number))
                continue
            try:
                expected_date = date.fromisoformat(condition.value)
            except ValueError:
                conditions.append(false())
                continue
            column = {
                "start": rows.c.start_date,
                "end": rows.c.end_date,
                "deadline": rows.c.deadline,
            }[field]
            conditions.extend((column.is_not(None), _compare(column, condition.operator, expected_date)))
        return conditions

    def read_page(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        allowed_project_ids: tuple[str, ...] | None,
        criteria: TaskWorkspaceCriteria,
        page: int,
        page_size: int,
        sort: ReadSort,
    ) -> TaskWorkspaceReadPage:
        if allowed_project_ids == ():
            return TaskWorkspaceReadPage(page=page, page_size=page_size)

        rows = self._effective_rows(
            tenant_id=tenant_id,
            organization_id=organization_id,
            allowed_project_ids=allowed_project_ids,
        )
        scope_conditions = [rows.c.project_id == criteria.project_id] if criteria.project_id else []
        current_date = criteria.as_of or date.today()
        summary_row = self._session.execute(
            select(
                func.count(rows.c.id).label("total"),
                func.sum(case((rows.c.status == TaskStatus.IN_PROGRESS.value, 1), else_=0)).label(
                    "in_progress"
                ),
                func.sum(case((rows.c.status == TaskStatus.BLOCKED.value, 1), else_=0)).label(
                    "blocked"
                ),
                func.sum(case((rows.c.status == TaskStatus.DONE.value, 1), else_=0)).label("done"),
                func.sum(
                    case(
                        (
                            (rows.c.deadline.is_not(None))
                            & (rows.c.deadline < current_date)
                            & (rows.c.status != TaskStatus.DONE.value),
                            1,
                        ),
                        else_=0,
                    )
                ).label("overdue"),
            ).where(*scope_conditions)
        ).one()
        summary = TaskWorkspaceSummary(
            total=int(summary_row.total or 0),
            in_progress=int(summary_row.in_progress or 0),
            blocked=int(summary_row.blocked or 0),
            done=int(summary_row.done or 0),
            overdue=int(summary_row.overdue or 0),
        )

        filtered_conditions = self._filtered_conditions(rows, criteria)
        filtered_total = int(
            self._session.scalar(select(func.count(rows.c.id)).where(*filtered_conditions)) or 0
        )
        sort_expressions = {
            "wbsCode": (
                func.lower(rows.c.project_name),
                rows.c.project_id,
                rows.c.wbs_code,
                rows.c.sort_order,
            ),
            "title": (func.lower(rows.c.name),),
            "taskName": (func.lower(rows.c.name),),
            "statusLabel": (rows.c.status,),
            "projectName": (func.lower(rows.c.project_name), rows.c.project_id),
            "priorityLabel": (rows.c.priority,),
            "priority": (rows.c.priority,),
            "startDateLabel": (rows.c.start_date,),
            "startDate": (rows.c.start_date,),
            "endDateLabel": (rows.c.end_date,),
            "endDate": (rows.c.end_date,),
            "progressValue": (rows.c.percent_complete,),
        }
        page_rows = self._session.execute(
            select(rows)
            .where(*filtered_conditions)
            .order_by(*stable_order_by(
                sort=sort,
                expressions=sort_expressions,
                default_key="wbsCode",
                tie_breakers=(rows.c.id,),
            ))
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return TaskWorkspaceReadPage(
            items=tuple(
                TaskWorkspaceReadItem(
                    id=str(row["id"]),
                    project_id=str(row["project_id"]),
                    project_name=str(row["project_name"] or ""),
                    name=str(row["name"] or ""),
                    code=str(row["code"] or ""),
                    description=str(row["description"] or ""),
                    status=str(row["status"] or TaskStatus.TODO.value),
                    start_date=row["start_date"],
                    end_date=row["end_date"],
                    duration_days=(
                        int(row["duration_days"])
                        if row["duration_days"] is not None
                        else None
                    ),
                    priority=int(row["priority"] or 0),
                    percent_complete=round(float(row["percent_complete"] or 0.0), 4),
                    actual_start=row["actual_start"],
                    actual_end=row["actual_end"],
                    deadline=row["deadline"],
                    version=int(row["version"] or 1),
                    parent_task_id=str(row["parent_task_id"] or "") or None,
                    wbs_code=str(row["wbs_code"] or ""),
                    sort_order=int(row["sort_order"] or 0),
                    is_summary=bool(row["is_summary"]),
                    hierarchy_depth=int(row["hierarchy_depth"] or 0),
                    child_count=int(row["child_count"] or 0),
                    is_milestone=bool(row["is_milestone"]),
                )
                for row in page_rows
            ),
            filtered_total=filtered_total,
            page=page,
            page_size=page_size,
            summary=summary,
            sort=sort,
        )


__all__ = ["SqlAlchemyTaskWorkspaceReader"]
