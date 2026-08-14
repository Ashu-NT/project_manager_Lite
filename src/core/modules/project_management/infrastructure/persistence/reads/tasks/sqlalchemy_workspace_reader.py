from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import String, case, cast, false, func, or_, select
from sqlalchemy.orm import Session, aliased
from src.core.modules.project_management.contracts.reads.sorting import ReadSort
from src.core.modules.project_management.infrastructure.persistence.reads.sorting import stable_order_by

from src.core.modules.project_management.contracts.reads.tasks import (
    TaskWorkspaceCriteria,
    TaskWorkspaceReadItem,
    TaskWorkspaceReadPage,
    TaskWorkspaceSummary,
)
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM


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
            "statusLabel": (rows.c.status,),
            "projectName": (func.lower(rows.c.project_name), rows.c.project_id),
            "priorityLabel": (rows.c.priority,),
            "startDateLabel": (rows.c.start_date,),
            "endDateLabel": (rows.c.end_date,),
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
