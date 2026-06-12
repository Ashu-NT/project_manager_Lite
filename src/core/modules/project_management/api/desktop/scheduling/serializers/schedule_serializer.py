"""Schedule item serializers."""

from src.core.modules.project_management.api.desktop.scheduling.models.schedule import SchedulingTaskDto
from src.core.modules.project_management.api.desktop.scheduling.utils.scheduling_utils import remaining_duration_days
from datetime import date


def serialize_schedule_item(item) -> SchedulingTaskDto:
    task = item.task
    return SchedulingTaskDto(
        id=task.id,
        project_id=task.project_id,
        name=task.name,
        description=getattr(task, "description", "") or "",
        status=task.status.value,
        status_label=task.status.value.replace("_", " ").title(),
        start_date=item.earliest_start,
        finish_date=item.earliest_finish,
        latest_start=item.latest_start,
        latest_finish=item.latest_finish,
        duration_days=getattr(task, "duration_days", None),
        remaining_duration_days=remaining_duration_days(
            getattr(task, "duration_days", None),
            float(task.percent_complete or 0.0),
        ),
        total_float_days=item.total_float_days,
        is_critical=item.is_critical,
        deadline=item.deadline,
        late_by_days=item.late_by_days,
        percent_complete=float(task.percent_complete or 0.0),
        actual_start=getattr(task, "actual_start", None),
        actual_end=getattr(task, "actual_end", None),
        priority=getattr(task, "priority", None),
    )


def serialize_task_as_schedule_item(task) -> SchedulingTaskDto:
    """Serialize a plain task domain object when no CPM data is available."""
    return SchedulingTaskDto(
        id=task.id,
        project_id=task.project_id,
        name=task.name,
        description=getattr(task, "description", "") or "",
        status=task.status.value,
        status_label=task.status.value.replace("_", " ").title(),
        start_date=task.start_date,
        finish_date=task.end_date,
        latest_start=None,
        latest_finish=None,
        duration_days=getattr(task, "duration_days", None),
        remaining_duration_days=remaining_duration_days(
            getattr(task, "duration_days", None),
            float(task.percent_complete or 0.0),
        ),
        total_float_days=None,
        is_critical=False,
        deadline=getattr(task, "deadline", None),
        late_by_days=None,
        percent_complete=float(task.percent_complete or 0.0),
        actual_start=getattr(task, "actual_start", None),
        actual_end=getattr(task, "actual_end", None),
        priority=getattr(task, "priority", None),
    )


__all__ = ["serialize_schedule_item", "serialize_task_as_schedule_item"]
