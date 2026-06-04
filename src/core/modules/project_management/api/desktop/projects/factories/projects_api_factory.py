"""Factory for building the projects desktop API."""

from src.core.modules.project_management.api.desktop.projects.api import (
    ProjectManagementProjectsDesktopApi,
)


def build_project_management_projects_desktop_api(
    *,
    project_service=None,
    project_resource_service=None,
    resource_service=None,
) -> ProjectManagementProjectsDesktopApi:
    return ProjectManagementProjectsDesktopApi(
        project_service=project_service,
        project_resource_service=project_resource_service,
        resource_service=resource_service,
    )


__all__ = ["build_project_management_projects_desktop_api"]
