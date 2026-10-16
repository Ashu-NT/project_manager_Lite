"""Factory for building the projects desktop API."""

from src.core.modules.project_management.api.desktop.projects.api import (
    ProjectManagementProjectsDesktopApi,
)


def build_project_management_projects_desktop_api(
    *,
    project_create=None,
    project_update=None,
    project_status=None,
    project_deletion=None,
    project_query=None,
    project_resource_query=None,
    project_resource_commands=None,
    resource_query=None,
) -> ProjectManagementProjectsDesktopApi:
    return ProjectManagementProjectsDesktopApi(
        project_create=project_create,
        project_update=project_update,
        project_status=project_status,
        project_deletion=project_deletion,
        project_query=project_query,
        project_resource_query=project_resource_query,
        project_resource_commands=project_resource_commands,
        resource_query=resource_query,
    )


__all__ = ["build_project_management_projects_desktop_api"]
