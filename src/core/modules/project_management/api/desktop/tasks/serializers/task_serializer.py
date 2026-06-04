from __future__ import annotations

from src.core.modules.project_management.api.desktop.tasks.models.task import TaskDesktopDto


def serialize_task(task, *, project_name: str) -> TaskDesktopDto:
    return TaskDesktopDto(
        id=task.id,
        project_id=task.project_id,
        project_name=project_name,
        name=task.name,
        code=getattr(task, "code", "") or "",
        description=task.description or "",
        status=task.status.value,
        status_label=task.status.value.replace("_", " ").title(),
        start_date=task.start_date,
        end_date=task.end_date,
        duration_days=task.duration_days,
        priority=task.priority,
        percent_complete=float(task.percent_complete or 0.0),
        actual_start=task.actual_start,
        actual_end=task.actual_end,
        deadline=task.deadline,
        version=task.version,
    )


__all__ = ["serialize_task"]
