"""Project management desktop API adapters."""

from src.core.modules.project_management.api.desktop.dashboard import (
    ProjectDashboardMetricDescriptor,
    ProjectDashboardOverviewDescriptor,
    ProjectManagementDashboardDesktopApi,
    build_project_management_dashboard_desktop_api,
)
from src.core.modules.project_management.api.desktop.workspaces import (
    ProjectManagementWorkspaceDescriptor,
    ProjectManagementWorkspaceDesktopApi,
    build_project_management_workspace_desktop_api,
)

__all__ = [
    "ProjectDashboardMetricDescriptor",
    "ProjectDashboardOverviewDescriptor",
    "ProjectManagementDashboardDesktopApi",
    "build_project_management_dashboard_desktop_api",
    "ProjectManagementWorkspaceDescriptor",
    "ProjectManagementWorkspaceDesktopApi",
    "build_project_management_workspace_desktop_api",
]
