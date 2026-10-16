from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.constraint_presentation import (
    constraint_presentation,
)
from src.core.modules.project_management.api.desktop.tasks.models.task import (
    TaskDesktopDto,
)
from src.core.modules.project_management.application.tasks.dto.responses.task import (
    TaskResponseDto,
)


def serialize_task(response: TaskResponseDto, *, project_name: str) -> TaskDesktopDto:
    return TaskDesktopDto(id=response.id, project_id=response.project_id, project_name=project_name, name=response.name, code=response.code, description=response.description, status=response.status, status_label=response.status.replace('_', ' ').title(), start_date=response.start_date, end_date=response.end_date, duration_days=response.duration_days, priority=response.priority, percent_complete=response.percent_complete, actual_start=response.actual_start, actual_end=response.actual_end, deadline=response.deadline, version=response.version, parent_task_id=response.parent_task_id, wbs_code=response.wbs_code, sort_order=response.sort_order, is_summary=response.is_summary, hierarchy_depth=response.hierarchy_depth, child_count=response.child_count, ancestor_ids=response.ancestor_ids, is_milestone=response.is_milestone, constraint_type=response.constraint_type, constraint_type_label=constraint_presentation(response.constraint_type or None).label, constraint_date=response.constraint_date)


__all__ = ["serialize_task"]
