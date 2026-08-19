"""Schedule item serializers."""

from src.core.modules.project_management.api.desktop.common.constraint_presentation import (
    constraint_presentation,
)
from src.core.modules.project_management.api.desktop.scheduling.models.schedule import SchedulingTaskDto


def serialize_schedule_item(item) -> SchedulingTaskDto:
    task = item.task
    presentation = constraint_presentation(getattr(task, "constraint_type", None))
    return SchedulingTaskDto(
        id=task.id,
        project_id=task.project_id,
        name=task.name,
        wbs_code=getattr(task, "wbs_code", "") or "",
        description=getattr(task, "description", "") or "",
        status=task.status.value,
        status_label=task.status.value.replace("_", " ").title(),
        start_date=item.earliest_start,
        finish_date=item.earliest_finish,
        latest_start=item.latest_start,
        latest_finish=item.latest_finish,
        duration_days=getattr(task, "duration_days", None),
        remaining_duration_days=task.remaining_duration_days,
        total_float_days=item.total_float_days,
        is_critical=item.is_critical,
        deadline=item.deadline,
        late_by_days=item.late_by_days,
        percent_complete=float(task.percent_complete or 0.0),
        actual_start=getattr(task, "actual_start", None),
        actual_end=getattr(task, "actual_end", None),
        priority=getattr(task, "priority", None),
        constraint_type=presentation.value.value if presentation.value is not None else "",
        constraint_type_label=presentation.label,
        constraint_date=getattr(task, "constraint_date", None),
    )


def serialize_task_as_schedule_item(task) -> SchedulingTaskDto:
    """Serialize a plain task domain object when no CPM data is available."""
    presentation = constraint_presentation(getattr(task, "constraint_type", None))
    return SchedulingTaskDto(
        id=task.id,
        project_id=task.project_id,
        name=task.name,
        wbs_code=getattr(task, "wbs_code", "") or "",
        description=getattr(task, "description", "") or "",
        status=task.status.value,
        status_label=task.status.value.replace("_", " ").title(),
        start_date=task.start_date,
        finish_date=task.end_date,
        latest_start=None,
        latest_finish=None,
        duration_days=getattr(task, "duration_days", None),
        remaining_duration_days=task.remaining_duration_days,
        total_float_days=None,
        is_critical=False,
        deadline=getattr(task, "deadline", None),
        late_by_days=None,
        percent_complete=float(task.percent_complete or 0.0),
        actual_start=getattr(task, "actual_start", None),
        actual_end=getattr(task, "actual_end", None),
        priority=getattr(task, "priority", None),
        constraint_type=presentation.value.value if presentation.value is not None else "",
        constraint_type_label=presentation.label,
        constraint_date=getattr(task, "constraint_date", None),
    )


__all__ = ["serialize_schedule_item", "serialize_task_as_schedule_item"]
