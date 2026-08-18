"""Project domain-to-DTO serializer."""

from collections.abc import Mapping
from decimal import Decimal

from src.core.modules.project_management.api.desktop.projects.models.project import ProjectDesktopDto
from src.core.modules.project_management.api.desktop.common.financial_formatting import format_budget
from src.core.platform.finance.money import canonical_decimal_text


def serialize_project(
    project,
    *,
    site_lookup: Mapping[str, str] | None = None,
    department_lookup: Mapping[str, str] | None = None,
    financial_currency_code: str = "",
    approved_budget: Decimal | None = None,
    client_label: str = "",
) -> ProjectDesktopDto:
    resolved_currency = str(financial_currency_code or "").strip().upper()
    normalized_site_id = str(getattr(project, "site_id", "") or "").strip() or None
    resolved_site_label = (
        (site_lookup or {}).get(normalized_site_id or "", "")
        if normalized_site_id
        else ""
    )
    normalized_department_id = str(getattr(project, "department_id", "") or "").strip() or None
    resolved_department_label = (
        (department_lookup or {}).get(normalized_department_id or "", "")
        if normalized_department_id
        else ""
    )
    # client_label is the authoritative DISPLAY value (resolved party name when
    # client_party_id is linked, otherwise the free-text client_name); it is
    # kept separate from client_name, which stays the raw editable field so the
    # edit dialog never round-trips a resolved party name into free text.
    resolved_client_label = str(client_label or "").strip() or str(project.client_name or "")
    return ProjectDesktopDto(
        id=project.id,
        name=project.name,
        code=getattr(project, "code", "") or "",
        description=project.description or "",
        status=project.status.value,
        status_label=project.status.value.replace("_", " ").title(),
        start_date=project.start_date,
        end_date=project.end_date,
        client_name=project.client_name,
        client_contact=project.client_contact,
        approved_budget=(
            None if approved_budget is None else canonical_decimal_text(approved_budget)
        ),
        approved_budget_label=format_budget(approved_budget, resolved_currency or None),
        financial_currency_code=resolved_currency,
        organization_id=getattr(project, "organization_id", None),
        site_id=normalized_site_id,
        site_label=resolved_site_label,
        department_id=normalized_department_id,
        department_label=resolved_department_label,
        client_party_id=getattr(project, "client_party_id", None),
        manager_user_id=getattr(project, "manager_user_id", None),
        version=project.version,
        client_label=resolved_client_label,
    )


__all__ = ["serialize_project"]
