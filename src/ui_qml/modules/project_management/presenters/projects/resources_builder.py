from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementProjectsDesktopApi,
)
from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_hourly_rate,
    format_hours,
)
from src.core.modules.project_management.application.resources.dto.responses.catalog import (
    ResourceResponse,
)
from src.core.modules.project_management.application.resources.dto.responses.project_resources import (
    ProjectResourceResponse,
)
from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogWorkspaceViewModel,
    ProjectRecordViewModel,
    ProjectSectionCollectionViewModel,
)

from .overview_builder import build_empty_overview


def to_project_resource_record(
    pr: ProjectResourceResponse, resource: ResourceResponse | None
) -> ProjectRecordViewModel:
    rate = (
        pr.hourly_rate
        if pr.hourly_rate is not None
        else (resource.hourly_rate if resource else None)
    )
    currency = pr.currency_code or (resource.currency_code if resource else None)
    return ProjectRecordViewModel(
        id=pr.id,
        title=resource.name if resource else pr.resource_id,
        status_label="Active" if pr.is_active else "Inactive",
        subtitle=(resource.role if resource else "") or "Team member",
        supporting_text=format_hours(pr.planned_hours),
        meta_text=format_hourly_rate(rate, currency),
        state={
            "projectResourceId": pr.id,
            "plannedHours": str(pr.planned_hours),
            "hourlyRate": str(rate) if rate is not None else "",
            "isActive": pr.is_active,
            "version": pr.version,
        },
    )


def assignable_resource_label(resource: ResourceResponse) -> str:
    details = [resource.role] if resource.role else []
    if resource.hourly_rate is not None:
        details.append(format_hourly_rate(resource.hourly_rate, resource.currency_code))
    return f"{resource.name} | {' | '.join(details)}" if details else resource.name


def build_project_resources_state(
    desktop_api: ProjectManagementProjectsDesktopApi,
    *,
    project_id: str,
) -> ProjectCatalogWorkspaceViewModel:
    normalized_project_id = (project_id or "").strip()
    resources = (
        desktop_api.list_project_resources(normalized_project_id)
        if normalized_project_id
        else ()
    )
    resource_by_id = (
        {
            row.id: row
            for row in desktop_api.list_resource_context(
                normalized_project_id,
                resource_ids=tuple(pr.resource_id for pr in resources),
            )
        }
        if resources
        else {}
    )
    items = tuple(
        sorted(
            (
                to_project_resource_record(pr, resource_by_id.get(pr.resource_id))
                for pr in resources
            ),
            key=lambda row: (not bool(row.state["isActive"]), row.title.casefold()),
        )
    )
    return ProjectCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_project_id=normalized_project_id,
        project_resources=ProjectSectionCollectionViewModel(
            title="Resources",
            subtitle=f"{len(items)} resource(s) assigned."
            if items
            else "Resources assigned to this project.",
            empty_state="No resources have been assigned to this project yet.",
            items=items,
        ),
    )


def build_assignable_resource_options(
    desktop_api: ProjectManagementProjectsDesktopApi,
    *,
    project_id: str,
) -> list[dict[str, str]]:
    normalized_project_id = (project_id or "").strip()
    if not normalized_project_id:
        return []
    options = desktop_api.list_assignable_resources(normalized_project_id)
    return sorted(
        [{"label": assignable_resource_label(opt), "value": opt.id} for opt in options],
        key=lambda row: row["label"].casefold(),
    )
