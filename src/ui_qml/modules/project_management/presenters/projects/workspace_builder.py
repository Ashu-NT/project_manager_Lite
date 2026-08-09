from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementProjectsDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogOverviewViewModel,
    ProjectCatalogWorkspaceViewModel,
    ProjectStatusOptionViewModel,
)

from .detail_builder import build_detail_view_model
from .filtering import build_empty_state, normalize_status_filter
from .overview_builder import build_overview
from .project_mapper import to_project_record
from .selection import resolve_selected_project_id


def build_workspace_state(
    desktop_api: ProjectManagementProjectsDesktopApi,
    *,
    search_text: str = "",
    status_filter: str = "all",
    selected_project_id: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> ProjectCatalogWorkspaceViewModel:
    status_options = (
        ProjectStatusOptionViewModel(value="all", label="All statuses"),
        *(
            ProjectStatusOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_statuses()
        ),
    )
    normalized_search = (search_text or "").strip()
    normalized_status_filter = normalize_status_filter(status_filter, status_options)
    project_page = desktop_api.list_project_page(
        search_text=normalized_search,
        status=normalized_status_filter,
        page=page,
        page_size=page_size,
    )
    paged_projects = project_page.items
    resolved_selected_project_id = resolve_selected_project_id(
        selected_project_id, paged_projects
    )
    selected_project = next(
        (p for p in paged_projects if p.id == resolved_selected_project_id),
        None,
    )
    return ProjectCatalogWorkspaceViewModel(
        overview=build_overview(
            total=project_page.total,
            filtered_total=project_page.filtered_total,
            active=project_page.active,
            planned=project_page.planned,
            on_hold=project_page.on_hold,
            completed=project_page.completed,
        ),
        status_options=status_options,
        selected_status_filter=normalized_status_filter,
        search_text=normalized_search,
        projects=tuple(to_project_record(project) for project in paged_projects),
        selected_project_id=resolved_selected_project_id,
        selected_project_detail=build_detail_view_model(selected_project),
        empty_state=build_empty_state(
            total=project_page.total,
            filtered_total=project_page.filtered_total,
            search_text=normalized_search,
            status_filter=normalized_status_filter,
        ),
        total_count=project_page.filtered_total,
        page=project_page.page,
        page_size=project_page.page_size,
    )


def build_project_detail_state(
    desktop_api: ProjectManagementProjectsDesktopApi,
    *,
    project_id: str,
) -> ProjectCatalogWorkspaceViewModel:
    normalized_project_id = (project_id or "").strip()
    all_projects = desktop_api.list_projects()
    selected_project = next(
        (p for p in all_projects if p.id == normalized_project_id),
        None,
    )
    return ProjectCatalogWorkspaceViewModel(
        overview=ProjectCatalogOverviewViewModel(
            title="Projects",
            subtitle="Project lifecycle, ownership, status, and list workflows.",
            metrics=(),
        ),
        selected_project_id=normalized_project_id if selected_project is not None else "",
        selected_project_detail=build_detail_view_model(selected_project),
    )
