from __future__ import annotations

from datetime import date, timedelta

from src.core.modules.project_management.application.tasks.workspace_filters import (
    build_task_workspace_criteria,
)
from src.core.modules.project_management.contracts.reads.tasks import (
    TaskWorkspaceReadItem,
    TaskWorkspaceReadPage,
    TaskWorkspaceSummary,
)
from src.core.modules.project_management.contracts.reads import ReadSort


def _status(task) -> str:
    value = getattr(task, "status", "")
    return str(getattr(value, "value", value) or "")


def _compare(actual, operator: str, expected) -> bool:
    resolved = "=" if operator == ":" else operator
    return {
        "=": actual == expected,
        ">=": actual >= expected,
        "<=": actual <= expected,
        ">": actual > expected,
        "<": actual < expected,
    }.get(resolved, False)


def build_fake_task_workspace_page(
    tasks,
    *,
    project_id=None,
    search_text="",
    status="all",
    priority="all",
    schedule="all",
    page=1,
    page_size=25,
    sort_key="wbsCode",
    sort_direction="asc",
    project_names=None,
):
    project_names = project_names or {
        "proj-1": "Plant Upgrade",
        "proj-2": "Warehouse Retrofit",
    }
    rows = list(tasks)
    if project_id:
        rows = [task for task in rows if task.project_id == project_id]
    criteria = build_task_workspace_criteria(
        project_id=project_id,
        search_text=search_text,
        status=status,
        priority=priority,
        schedule=schedule,
        as_of=date.today(),
    )

    def matches(task) -> bool:
        task_status = _status(task)
        if criteria.status != "ALL" and task_status != criteria.status:
            return False
        task_priority = int(getattr(task, "priority", 0) or 0)
        if criteria.priority == "high" and task_priority < 70:
            return False
        if criteria.priority == "medium" and not 30 <= task_priority <= 69:
            return False
        if criteria.priority == "low" and task_priority >= 30:
            return False
        deadline = getattr(task, "deadline", None)
        if criteria.schedule == "overdue" and not (deadline and deadline < criteria.as_of):
            return False
        if criteria.schedule == "due_7" and not (
            deadline and criteria.as_of <= deadline <= criteria.as_of + timedelta(days=7)
        ):
            return False
        if criteria.schedule == "no_deadline" and deadline is not None:
            return False
        haystack = " ".join(
            (
                str(getattr(task, "name", "") or ""),
                str(getattr(task, "description", "") or ""),
                project_names.get(task.project_id, ""),
            )
        ).casefold()
        if any(term not in haystack for term in criteria.search_terms):
            return False
        for condition in criteria.conditions:
            if condition.field == "status":
                if condition.operator in {":", "="} and task_status != condition.value.upper():
                    return False
                continue
            if condition.field in {"priority", "progress"}:
                try:
                    expected = float(condition.value)
                except ValueError:
                    return False
                actual = (
                    task_priority
                    if condition.field == "priority"
                    else float(getattr(task, "percent_complete", 0.0) or 0.0)
                )
            else:
                try:
                    expected = date.fromisoformat(condition.value)
                except ValueError:
                    return False
                actual = getattr(
                    task,
                    {"start": "start_date", "end": "end_date", "deadline": "deadline"}[
                        condition.field
                    ],
                    None,
                )
                if actual is None:
                    return False
            if not _compare(actual, condition.operator, expected):
                return False
        return True

    sort = ReadSort.normalize(
        key=sort_key,
        direction=sort_direction,
        allowed_keys={
            "wbsCode",
            "title",
            "statusLabel",
            "projectName",
            "priorityLabel",
            "startDateLabel",
            "endDateLabel",
            "progressValue",
        },
        default_key="wbsCode",
    )
    key_by_sort = {
        "wbsCode": lambda task: (
            project_names.get(task.project_id, "").casefold(),
            str(getattr(task, "wbs_code", task.id) or task.id),
            int(getattr(task, "sort_order", 0) or 0),
        ),
        "title": lambda task: (str(getattr(task, "name", "")).casefold(),),
        "statusLabel": lambda task: (_status(task),),
        "projectName": lambda task: (project_names.get(task.project_id, "").casefold(),),
        "priorityLabel": lambda task: (int(getattr(task, "priority", 0) or 0),),
        "startDateLabel": lambda task: (getattr(task, "start_date", None) or date.min,),
        "endDateLabel": lambda task: (getattr(task, "end_date", None) or date.min,),
        "progressValue": lambda task: (float(getattr(task, "percent_complete", 0) or 0),),
    }
    filtered = [task for task in rows if matches(task)]
    filtered.sort(
        key=lambda task: (*key_by_sort[sort.key](task), task.id),
        reverse=sort.direction.value == "desc",
    )
    offset = (page - 1) * page_size
    items = tuple(
        TaskWorkspaceReadItem(
            id=task.id,
            project_id=task.project_id,
            project_name=project_names.get(task.project_id, ""),
            name=task.name,
            code=str(getattr(task, "code", "") or ""),
            description=str(getattr(task, "description", "") or ""),
            status=_status(task),
            start_date=getattr(task, "start_date", None),
            end_date=getattr(task, "end_date", None),
            duration_days=getattr(task, "duration_days", None),
            priority=int(getattr(task, "priority", 0) or 0),
            percent_complete=float(getattr(task, "percent_complete", 0.0) or 0.0),
            actual_start=getattr(task, "actual_start", None),
            actual_end=getattr(task, "actual_end", None),
            deadline=getattr(task, "deadline", None),
            version=int(getattr(task, "version", 1) or 1),
            parent_task_id=getattr(task, "parent_task_id", None),
            wbs_code=str(getattr(task, "wbs_code", task.id) or task.id),
            sort_order=int(getattr(task, "sort_order", 0) or 0),
            is_summary=False,
            hierarchy_depth=0,
            child_count=0,
        )
        for task in filtered[offset : offset + page_size]
    )
    return TaskWorkspaceReadPage(
        items=items,
        filtered_total=len(filtered),
        page=page,
        page_size=page_size,
        summary=TaskWorkspaceSummary(
            total=len(rows),
            in_progress=sum(_status(task) == "IN_PROGRESS" for task in rows),
            blocked=sum(_status(task) == "BLOCKED" for task in rows),
            done=sum(_status(task) == "DONE" for task in rows),
            overdue=sum(
                bool(getattr(task, "deadline", None))
                and task.deadline < date.today()
                and _status(task) != "DONE"
                for task in rows
            ),
        ),
        sort=sort,
    )


__all__ = ["build_fake_task_workspace_page"]
