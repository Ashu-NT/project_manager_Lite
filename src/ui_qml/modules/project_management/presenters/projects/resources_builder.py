from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementProjectsDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogWorkspaceViewModel,
    ProjectRecordViewModel,
    ProjectSectionCollectionViewModel,
)

from .overview_builder import build_empty_overview


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
    items = tuple(
        ProjectRecordViewModel(
            id=pr.id,
            title=pr.resource_name,
            status_label=pr.status_label,
            subtitle=pr.role or "Team member",
            supporting_text=pr.planned_hours_label,
            meta_text=pr.hourly_rate_label,
            state={
                "projectResourceId": pr.id,
                "plannedHours": pr.planned_hours,
                "hourlyRate": pr.hourly_rate if pr.hourly_rate is not None else "",
                "isActive": pr.is_active,
            },
        )
        for pr in resources
    )
    return ProjectCatalogWorkspaceViewModel(
        overview=build_empty_overview(),
        selected_project_id=normalized_project_id,
        project_resources=ProjectSectionCollectionViewModel(
            title="Resources",
            subtitle=f"{len(items)} resource(s) assigned." if items else "Resources assigned to this project.",
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
    return [{"label": opt.label, "value": opt.value} for opt in options]
