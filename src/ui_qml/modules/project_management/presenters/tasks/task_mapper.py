from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.tasks import TaskRecordViewModel

from .formatting import format_date, format_date_label

def build_task_state(task: Any) -> dict[str, object]:
    duration_value = task.duration_days if task.duration_days is not None else ""
    priority_value = task.priority if task.priority is not None else ""
    return {
        "taskId": task.id,
        "projectId": task.project_id,
        "projectName": task.project_name or "",
        "name": task.name,
        "taskCode": getattr(task, "code", "") or "",
        "description": task.description or "",
        "status": task.status,
        "statusLabel": task.status_label,
        "startDate": format_date(task.start_date),
        "startDateLabel": format_date_label(task.start_date),
        "endDate": format_date(task.end_date),
        "endDateLabel": format_date_label(task.end_date),
        "durationDays": str(duration_value),
        "durationLabel": (
            f"{duration_value} day(s)" if duration_value != "" else "Not set"
        ),
        "deadline": format_date(task.deadline),
        "deadlineLabel": format_date_label(task.deadline),
        "priority": str(priority_value),
        "priorityLabel": (
            str(priority_value) if priority_value != "" else "Not set"
        ),
        "percentComplete": f"{float(task.percent_complete or 0.0):.1f}",
        "percentCompleteLabel": f"{float(task.percent_complete or 0.0):.1f}%",
        "actualStart": format_date(task.actual_start),
        "actualStartLabel": format_date_label(task.actual_start),
        "actualEnd": format_date(task.actual_end),
        "actualEndLabel": format_date_label(task.actual_end),
        "version": task.version,
    }

def to_task_record_view_model(task: Any) -> TaskRecordViewModel:
    state = build_task_state(task)
    return TaskRecordViewModel(
        id=task.id,
        title=task.name,
        status_label=task.status_label,
        subtitle=(
            f"{state['projectName']} | Start {state['startDateLabel']} | "
            f"Finish {state['endDateLabel']}"
        ),
        supporting_text=(
            f"Progress: {state['percentCompleteLabel']} | "
            f"Deadline: {state['deadlineLabel']} | "
            f"Priority: {state['priorityLabel']}"
        ),
        meta_text=task.description or "No task description has been added yet.",
        state=state,
    )
