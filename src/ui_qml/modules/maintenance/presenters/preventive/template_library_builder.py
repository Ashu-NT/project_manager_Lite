from __future__ import annotations

from .task_step_detail_builder import build_task_step_detail
from .task_step_mapper import task_step_record
from .task_template_detail_builder import build_task_template_detail
from .task_template_mapper import task_template_record


def build_template_empty_state(
    *,
    template_rows_all,
    search_text: str,
    active_filter: str,
    maintenance_type_filter: str,
    status_filter: str,
) -> str:
    if template_rows_all:
        return ""
    if (
        search_text
        or active_filter != "all"
        or maintenance_type_filter != "all"
        or status_filter != "all"
    ):
        return "No task templates match the current filters."
    return "No task templates are available yet. Create a template to seed the preventive library."


def build_template_library_state(
    *,
    active_filter_options,
    task_template_type_options,
    task_template_status_options,
    normalized_template_active_filter: str,
    normalized_template_maintenance_type_filter: str,
    normalized_template_status_filter: str,
    normalized_template_search: str,
    template_rows_all,
    resolved_task_template_id: str,
    selected_task_template,
    step_rows,
    resolved_task_step_id: str,
    selected_task_step,
) -> dict[str, object]:
    return {
        "activeOptions": active_filter_options,
        "maintenanceTypeOptions": task_template_type_options,
        "statusOptions": task_template_status_options,
        "selectedActiveFilter": normalized_template_active_filter,
        "selectedMaintenanceTypeFilter": normalized_template_maintenance_type_filter,
        "selectedStatusFilter": normalized_template_status_filter,
        "searchText": normalized_template_search,
        "templates": {
            "title": "Task Templates",
            "subtitle": "Reusable preventive task templates with versioned instructions, permit flags, and step libraries.",
            "emptyState": build_template_empty_state(
                template_rows_all=template_rows_all,
                search_text=normalized_template_search,
                active_filter=normalized_template_active_filter,
                maintenance_type_filter=normalized_template_maintenance_type_filter,
                status_filter=normalized_template_status_filter,
            ),
            "items": [task_template_record(row) for row in template_rows_all],
        },
        "selectedTaskTemplateId": resolved_task_template_id,
        "selectedTaskTemplate": build_task_template_detail(selected_task_template),
        "steps": {
            "title": "Task Steps",
            "subtitle": "Step instructions, hint levels, confirmation flags, and measurement expectations for the selected template.",
            "emptyState": (
                "Select a task template to review its step library."
                if not resolved_task_template_id
                else "No step templates are configured for the selected task template yet."
            ),
            "items": [task_step_record(row) for row in step_rows],
        },
        "selectedTaskStepId": resolved_task_step_id,
        "selectedTaskStep": build_task_step_detail(selected_task_step),
    }
