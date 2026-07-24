from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectRecordViewModel,
)

from .formatting import format_date, format_date_label

def build_project_state(project: Any) -> dict[str, object]:
    return {
        "projectId": project.id,
        "name": project.name,
        "projectCode": getattr(project, "code", "") or "",
        "status": project.status,
        "statusLabel": project.status_label,
        "clientName": project.client_name or "",
        "clientContact": project.client_contact or "",
        "startDate": format_date(project.start_date),
        "startDateLabel": format_date_label(project.start_date),
        "endDate": format_date(project.end_date),
        "endDateLabel": format_date_label(project.end_date),
        "plannedBudget": (
            "" if project.planned_budget is None else f"{float(project.planned_budget):.2f}"
        ),
        "plannedBudgetLabel": project.planned_budget_label,
        "currency": project.currency or "",
        "organizationId": getattr(project, "organization_id", None) or "",
        "siteId": getattr(project, "site_id", None) or "",
        "siteLabel": getattr(project, "site_label", "") or "",
        "description": project.description or "",
        "version": project.version,
    }

def to_project_record(project: Any) -> ProjectRecordViewModel:
    state = build_project_state(project)
    client_text = state["clientName"] or "No client assigned"
    contact_text = state["clientContact"] or "No client contact recorded"
    site_text = state["siteLabel"] or "No site assigned"
    return ProjectRecordViewModel(
        id=project.id,
        title=project.name,
        status_label=project.status_label,
        subtitle=f"{client_text} | {site_text}",
        supporting_text=(
            f"Schedule: {state['startDateLabel']} -> {state['endDateLabel']} | "
            f"Budget: {state['plannedBudgetLabel']}"
        ),
        meta_text=contact_text if contact_text != "No client contact recorded" else (
            project.description or "No project description has been added yet."
        ),
        state=state,
    )
