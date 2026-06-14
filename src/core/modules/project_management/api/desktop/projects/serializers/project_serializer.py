"""Project domain-to-DTO serializer."""

from collections.abc import Mapping

from src.core.modules.project_management.api.desktop.projects.models.project import ProjectDesktopDto
from src.core.modules.project_management.api.desktop.projects.formatters.resource_formatters import format_budget


def serialize_project(
    project,
    *,
    site_lookup: Mapping[str, str] | None = None,
) -> ProjectDesktopDto:
    resolved_currency = (project.currency or "").strip().upper() or None
    normalized_site_id = str(getattr(project, "site_id", "") or "").strip() or None
    resolved_site_label = (
        (site_lookup or {}).get(normalized_site_id or "", "")
        if normalized_site_id
        else ""
    )
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
        planned_budget=project.planned_budget,
        planned_budget_label=format_budget(project.planned_budget, resolved_currency),
        currency=resolved_currency,
        organization_id=getattr(project, "organization_id", None),
        site_id=normalized_site_id,
        site_label=resolved_site_label,
        client_party_id=getattr(project, "client_party_id", None),
        manager_user_id=getattr(project, "manager_user_id", None),
        version=project.version,
    )


__all__ = ["serialize_project"]
