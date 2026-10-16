from __future__ import annotations

from decimal import Decimal

from src.core.modules.project_management.application.projects.dto.responses.project import (
    ProjectResponse,
)
from src.core.modules.project_management.domain.projects.project import Project


def map_project_response(
    project: Project,
    *,
    financial_currency_code: str = "",
    approved_budget: Decimal | None = None,
    approved_budget_currency: str = "",
    approved_budget_visible: bool = False,
) -> ProjectResponse:
    """Map already-authorized evidence; do not query or manufacture a budget."""
    return ProjectResponse(
        id=project.id,
        name=project.name,
        code=project.code,
        description=project.description or "",
        status=project.status,
        start_date=project.start_date,
        end_date=project.end_date,
        client_name=project.client_name,
        client_contact=project.client_contact,
        organization_id=project.organization_id,
        site_id=project.site_id,
        department_id=project.department_id,
        client_party_id=project.client_party_id,
        manager_user_id=project.manager_user_id,
        version=project.version,
        financial_currency_code=financial_currency_code.strip().upper(),
        approved_budget=approved_budget if approved_budget_visible else None,
        approved_budget_currency=(approved_budget_currency.strip().upper() if approved_budget_visible else ""),
        approved_budget_visible=approved_budget_visible,
    )


