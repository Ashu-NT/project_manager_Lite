from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.tasks import TaskRecordViewModel

from .formatting import format_date, format_date_label

# Bucket boundaries kept identical to the Priority filter's own buckets
# (`build_task_priority_options`) and the SQL reader's predicate
# (`sqlalchemy_workspace_reader.py`: >=70 high, 30-69 medium, <30 low) --
# the displayed label must agree with what the filter actually selects.
def _priority_bucket_label(priority_value: object) -> str:
    if priority_value == "" or priority_value is None:
        return "Not set"
    value = int(priority_value)
    if value >= 70:
        return "High"
    if value >= 30:
        return "Medium"
    return "Low"

def build_task_state(task: Any) -> dict[str, object]:
    duration_value = task.duration_days if task.duration_days is not None else ""
    priority_value = task.priority if task.priority is not None else ""
    return {
        "taskId": task.id,
        "projectId": task.project_id,
        "projectName": task.project_name or "",
        "name": task.name,
        "taskCode": getattr(task, "code", "") or "",
        "parentTaskId": getattr(task, "parent_task_id", None) or "",
        "wbsCode": getattr(task, "wbs_code", "") or "",
        "sortOrder": int(getattr(task, "sort_order", 0) or 0),
        "isSummary": bool(getattr(task, "is_summary", False)),
        "hierarchyDepth": int(getattr(task, "hierarchy_depth", 0) or 0),
        "childCount": int(getattr(task, "child_count", 0) or 0),
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
        "priorityLabel": _priority_bucket_label(priority_value),
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
        title=f"{'    ' * state['hierarchyDepth']}{task.name}",
        status_label=task.status_label,
        subtitle=(
            f"WBS {state['wbsCode']} | {state['projectName']} | Start {state['startDateLabel']} | "
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
