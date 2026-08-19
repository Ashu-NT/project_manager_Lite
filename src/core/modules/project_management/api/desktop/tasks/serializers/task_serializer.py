from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.models.task import TaskDesktopDto


def serialize_task(task, *, project_name: str, hierarchy_node=None, rollup=None) -> TaskDesktopDto:
    is_summary = bool(getattr(hierarchy_node, "is_summary", False))
    status = rollup.status if is_summary and rollup is not None else task.status
    return TaskDesktopDto(
        id=task.id,
        project_id=task.project_id,
        project_name=project_name,
        name=task.name,
        code=getattr(task, "code", "") or "",
        description=task.description or "",
        status=status.value,
        status_label=status.value.replace("_", " ").title(),
        start_date=rollup.start_date if is_summary and rollup is not None else task.start_date,
        end_date=rollup.end_date if is_summary and rollup is not None else task.end_date,
        duration_days=rollup.duration_days if is_summary and rollup is not None else task.duration_days,
        priority=task.priority,
        percent_complete=(
            float(rollup.percent_complete)
            if is_summary and rollup is not None
            else float(task.percent_complete or 0.0)
        ),
        actual_start=task.actual_start,
        actual_end=task.actual_end,
        deadline=task.deadline,
        version=task.version,
        parent_task_id=getattr(task, "parent_task_id", None),
        wbs_code=getattr(task, "wbs_code", "") or "",
        sort_order=int(getattr(task, "sort_order", 0) or 0),
        is_summary=is_summary,
        hierarchy_depth=int(getattr(hierarchy_node, "depth", 0) or 0),
        child_count=int(getattr(hierarchy_node, "child_count", 0) or 0),
        ancestor_ids=tuple(getattr(hierarchy_node, "ancestor_ids", ()) or ()),
        is_milestone=bool(getattr(task, "is_milestone", False)),
    )


__all__ = ["serialize_task"]
