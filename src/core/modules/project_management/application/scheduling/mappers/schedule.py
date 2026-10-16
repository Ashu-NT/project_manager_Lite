"""Copy canonical CPM/task facts once at the application boundary."""

from src.core.modules.project_management.application.scheduling.dto.responses.schedule import (
    SchedulingTaskResponse,
)
from src.core.modules.project_management.application.scheduling.models.cpm import (
    CPMTaskInfo,
)


def map_schedule_item(item: CPMTaskInfo) -> SchedulingTaskResponse:
    task = item.task
    constraint = getattr(task, "constraint_type", None)
    return SchedulingTaskResponse(
        id=task.id,
        project_id=task.project_id,
        code=getattr(task, "code", "") or "",
        name=task.name,
        parent_task_id=getattr(task, "parent_task_id", None),
        wbs_code=getattr(task, "wbs_code", "") or "",
        sort_order=int(getattr(task, "sort_order", 0) or 0),
        is_milestone=bool(getattr(task, "is_milestone", False)),
        description=getattr(task, "description", "") or "",
        status=task.status.value,
        start_date=item.earliest_start,
        finish_date=item.earliest_finish,
        latest_start=item.latest_start,
        latest_finish=item.latest_finish,
        duration_days=getattr(task, "duration_days", None),
        remaining_duration_days=task.remaining_duration_days,
        total_float_days=item.total_float_days,
        is_critical=item.is_critical,
        is_infeasible=getattr(item, "is_infeasible", False),
        deadline=item.deadline,
        late_by_days=item.late_by_days,
        percent_complete=float(task.percent_complete or 0.0),
        actual_start=getattr(task, "actual_start", None),
        actual_end=getattr(task, "actual_end", None),
        priority=getattr(task, "priority", None),
        constraint_type=str(getattr(constraint, "value", constraint) or ""),
        constraint_date=getattr(task, "constraint_date", None),
    )
