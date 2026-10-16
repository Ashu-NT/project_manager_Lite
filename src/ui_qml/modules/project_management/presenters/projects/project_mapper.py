from __future__ import annotations

from collections.abc import Mapping

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_budget,
)
from src.core.modules.project_management.application.projects.dto.responses.project import (
    ProjectResponse,
)
from src.core.modules.project_management.contracts.reads.projects.models import (
    ProjectCatalogReadItem,
)
from src.core.platform.domain.finance.money import canonical_decimal_text
from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectRecordViewModel,
)

from .formatting import format_date, format_date_label


def build_project_state(
    response: ProjectResponse | ProjectCatalogReadItem,
    *,
    department_labels: Mapping[str, str] | None = None,
) -> dict[str, object]:
    project = (
        response.project if isinstance(response, ProjectCatalogReadItem) else response
    )
    status = project.status.value
    return {
        "projectId": project.id,
        "name": project.name,
        "projectCode": getattr(project, "code", "") or "",
        "status": status,
        "statusLabel": status.replace("_", " ").title(),
        "clientName": project.client_name or "",
        "clientLabel": (
            response.client_label
            if isinstance(response, ProjectCatalogReadItem)
            else ""
        )
        or project.client_name
        or "",
        "clientContact": project.client_contact or "",
        "startDate": format_date(project.start_date),
        "startDateLabel": format_date_label(project.start_date),
        "endDate": format_date(project.end_date),
        "endDateLabel": format_date_label(project.end_date),
        "approvedBudget": ""
        if response.approved_budget is None
        else canonical_decimal_text(response.approved_budget),
        "approvedBudgetLabel": format_budget(
            response.approved_budget, response.approved_budget_currency or None
        )
        if response.approved_budget_visible
        else "",
        "approvedBudgetCurrency": response.approved_budget_currency
        if response.approved_budget_visible
        else "",
        "approvedBudgetVisible": response.approved_budget_visible,
        "financialCurrencyCode": response.financial_currency_code or "",
        "organizationId": getattr(project, "organization_id", None) or "",
        "siteId": getattr(project, "site_id", None) or "",
        "siteLabel": response.site_label
        if isinstance(response, ProjectCatalogReadItem)
        else "",
        "departmentId": getattr(project, "department_id", None) or "",
        "departmentLabel": (department_labels or {}).get(
            project.department_id or "", ""
        ),
        "managerUserId": project.manager_user_id or "",
        "clientPartyId": project.client_party_id or "",
        "description": project.description or "",
        "version": project.version,
    }


def to_project_record(
    response: ProjectResponse | ProjectCatalogReadItem,
    *,
    department_labels: Mapping[str, str] | None = None,
) -> ProjectRecordViewModel:
    state = build_project_state(response, department_labels=department_labels)
    project = (
        response.project if isinstance(response, ProjectCatalogReadItem) else response
    )
    client_text = state["clientLabel"] or "No client assigned"
    contact_text = str(state["clientContact"] or "No client contact recorded")
    site_text = state["siteLabel"] or "No site assigned"
    supporting_parts = [
        f"Schedule: {state['startDateLabel']} -> {state['endDateLabel']}"
    ]
    if state["approvedBudgetVisible"]:
        supporting_parts.append(f"Approved budget: {state['approvedBudgetLabel']}")
    return ProjectRecordViewModel(
        id=project.id,
        title=project.name,
        status_label=str(state["statusLabel"]),
        subtitle=f"{client_text} | {site_text}",
        supporting_text=" | ".join(supporting_parts),
        meta_text=contact_text
        if contact_text != "No client contact recorded"
        else (project.description or "No project description has been added yet."),
        state=state,
    )
