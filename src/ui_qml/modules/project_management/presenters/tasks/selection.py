from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskSelectorOptionViewModel,
)

def resolve_project_id(
    project_id: str | None,
    project_options: tuple[TaskSelectorOptionViewModel, ...],
) -> str:
    normalized_id = (project_id or "").strip()
    option_values = {option.value for option in project_options}
    if normalized_id in option_values:
        return normalized_id
    return ""

def resolve_task_id(selected_task_id: str | None, filtered_tasks: Any) -> str:
    normalized_id = (selected_task_id or "").strip()
    if normalized_id and any(task.id == normalized_id for task in filtered_tasks):
        return normalized_id
    if filtered_tasks:
        return filtered_tasks[0].id
    return ""

def resolve_assignment_id(selected_assignment_id: str | None, assignments: Any) -> str:
    normalized_id = (selected_assignment_id or "").strip()
    available_values = [str(assignment.id or "") for assignment in assignments]
    if normalized_id and normalized_id in available_values:
        return normalized_id
    return available_values[0] if available_values else ""

def resolve_time_entry_id(selected_time_entry_id: str | None, entries: Any) -> str:
    normalized_id = (selected_time_entry_id or "").strip()
    available_values = [str(entry.entry_id or "") for entry in entries]
    if normalized_id and normalized_id in available_values:
        return normalized_id
    return available_values[0] if available_values else ""
