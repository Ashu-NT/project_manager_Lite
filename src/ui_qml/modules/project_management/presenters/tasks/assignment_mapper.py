from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskRecordViewModel,
    TaskSelectorOptionViewModel,
)


def to_assignment_record_view_model(assignment) -> TaskRecordViewModel:
    allocation_percent = float(assignment.allocation_percent or 0.0)
    hours_logged = float(assignment.hours_logged or 0.0)
    state = {
        "assignmentId": assignment.id,
        "taskId": assignment.task_id,
        "resourceId": assignment.resource_id,
        "resourceName": assignment.resource_name,
        "allocationPercent": f"{allocation_percent:.1f}",
        "hoursLogged": f"{hours_logged:.2f}",
        "projectResourceId": assignment.project_resource_id or "",
    }
    return TaskRecordViewModel(
        id=assignment.id,
        title=assignment.resource_name,
        status_label=f"{allocation_percent:.1f}%",
        subtitle="Current allocation commitment",
        supporting_text=f"Hours logged: {hours_logged:.2f}",
        meta_text=f"Resource ID: {assignment.resource_id}",
        state=state,
    )


def build_assignment_options(
    desktop_api,
    project_id: str | None,
) -> tuple[TaskSelectorOptionViewModel, ...]:
    try:
        options = desktop_api.list_project_resources(project_id)
    except Exception:
        return ()
    return tuple(
        TaskSelectorOptionViewModel(value=option.value, label=option.label)
        for option in options
    )


def build_time_assignment_options(
    assignments,
) -> tuple[TaskSelectorOptionViewModel, ...]:
    options: list[TaskSelectorOptionViewModel] = []
    for assignment in assignments:
        resource_name = str(
            getattr(assignment, "resource_name", "")
            or getattr(assignment, "resource_id", "")
            or "Assignment"
        )
        allocation_percent = float(getattr(assignment, "allocation_percent", 0.0) or 0.0)
        label = (
            f"{resource_name} | {allocation_percent:g}% allocation"
            if allocation_percent > 0
            else resource_name
        )
        options.append(
            TaskSelectorOptionViewModel(
                value=str(getattr(assignment, "id", "") or ""),
                label=label,
            )
        )
    return tuple(options)
