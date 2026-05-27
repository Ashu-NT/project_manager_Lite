from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementWorkspaceDesktopApi,
    build_project_management_workspace_desktop_api,
)
from src.ui_qml.modules.project_management.routes import build_project_management_routes
from src.ui_qml.modules.project_management.view_models.workspace import (
    ProjectManagementWorkspaceViewModel,
)


class ProjectManagementWorkspacePresenter:
    def __init__(
        self,
        route_id: str,
        desktop_api: ProjectManagementWorkspaceDesktopApi | None = None,
    ) -> None:
        self._route_id = route_id
        self._desktop_api = desktop_api or build_project_management_workspace_desktop_api()

    def build_view_model(self) -> ProjectManagementWorkspaceViewModel:
        route_by_id = {route.route_id: route for route in build_project_management_routes()}
        route = route_by_id[self._route_id]
        descriptor = self._desktop_api.get_workspace(route.route_id)
        summary = descriptor.summary if descriptor is not None else ""
        return ProjectManagementWorkspaceViewModel(
            route_id=route.route_id,
            title=route.title,
            summary=summary,
            migration_status="QML landing zone ready",
            legacy_runtime_status="Existing QWidget screen remains active",
        )


def build_project_management_workspace_presenters() -> dict[
    str, ProjectManagementWorkspacePresenter
]:
    desktop_api = build_project_management_workspace_desktop_api()
    return {
        route.route_id: ProjectManagementWorkspacePresenter(route.route_id, desktop_api)
        for route in build_project_management_routes()
    }


__all__ = [
    "ProjectManagementWorkspacePresenter",
    "build_project_management_workspace_presenters",
]
