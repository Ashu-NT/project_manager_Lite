from __future__ import annotations

from .models import ImportFieldSpec


IMPORT_SCHEMAS: dict[str, tuple[ImportFieldSpec, ...]] = {
    "projects": (
        ImportFieldSpec("id", "Project ID"),
        ImportFieldSpec("name", "Name", required=True),
        ImportFieldSpec("description", "Description"),
        ImportFieldSpec("client_name", "Client"),
        ImportFieldSpec("client_contact", "Client Contact"),
        ImportFieldSpec("planned_budget", "Planned Budget"),
        ImportFieldSpec("currency", "Currency"),
        ImportFieldSpec("start_date", "Start Date"),
        ImportFieldSpec("end_date", "End Date"),
        ImportFieldSpec("status", "Status"),
    ),
    "resources": (
        ImportFieldSpec("id", "Resource ID"),
        ImportFieldSpec("name", "Name", required=True),
        ImportFieldSpec("role", "Role"),
        ImportFieldSpec("hourly_rate", "Hourly Rate"),
        ImportFieldSpec("is_active", "Active"),
        ImportFieldSpec("cost_type", "Cost Type"),
        ImportFieldSpec("currency_code", "Currency"),
        ImportFieldSpec("capacity_percent", "Capacity %"),
        ImportFieldSpec("address", "Address"),
        ImportFieldSpec("contact", "Contact"),
    ),
    "tasks": (
        ImportFieldSpec("id", "Task ID"),
        ImportFieldSpec("project_id", "Project ID"),
        ImportFieldSpec("project_name", "Project Name"),
        ImportFieldSpec("name", "Task Name", required=True),
        ImportFieldSpec("description", "Description"),
        ImportFieldSpec("start_date", "Start Date"),
        ImportFieldSpec("duration_days", "Duration Days"),
        ImportFieldSpec("priority", "Priority"),
        ImportFieldSpec("deadline", "Deadline"),
        ImportFieldSpec("status", "Status"),
        ImportFieldSpec("percent_complete", "Percent Complete"),
    ),
    "costs": (
        ImportFieldSpec("id", "Cost ID"),
        ImportFieldSpec("project_id", "Project ID"),
        ImportFieldSpec("project_name", "Project Name"),
        ImportFieldSpec("task_id", "Task ID"),
        ImportFieldSpec("task_name", "Task Name"),
        ImportFieldSpec("description", "Description", required=True),
        ImportFieldSpec("planned_amount", "Planned Amount"),
        ImportFieldSpec("committed_amount", "Committed Amount"),
        ImportFieldSpec("actual_amount", "Actual Amount"),
        ImportFieldSpec("cost_type", "Cost Type"),
        ImportFieldSpec("currency_code", "Currency"),
        ImportFieldSpec("incurred_date", "Incurred Date"),
    ),
}


__all__ = ["IMPORT_SCHEMAS"]
