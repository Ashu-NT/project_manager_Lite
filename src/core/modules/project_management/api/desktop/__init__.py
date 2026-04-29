"""Project management desktop API adapters."""

from src.core.modules.project_management.api.desktop.dashboard import (
    ProjectDashboardChartDescriptor,
    ProjectDashboardChartPointDescriptor,
    ProjectDashboardMetricDescriptor,
    ProjectDashboardOverviewDescriptor,
    ProjectDashboardPanelDescriptor,
    ProjectDashboardPanelRowDescriptor,
    ProjectDashboardSectionDescriptor,
    ProjectDashboardSectionItemDescriptor,
    ProjectDashboardSelectorOptionDescriptor,
    ProjectDashboardSnapshotDescriptor,
    ProjectManagementDashboardDesktopApi,
    build_project_management_dashboard_desktop_api,
)
from src.core.modules.project_management.api.desktop.workspaces import (
    ProjectManagementWorkspaceDescriptor,
    ProjectManagementWorkspaceDesktopApi,
    build_project_management_workspace_desktop_api,
)

__all__ = [
    "ProjectDashboardChartDescriptor",
    "ProjectDashboardChartPointDescriptor",
    "ProjectDashboardMetricDescriptor",
    "ProjectDashboardOverviewDescriptor",
    "ProjectDashboardPanelDescriptor",
    "ProjectDashboardPanelRowDescriptor",
    "ProjectDashboardSectionDescriptor",
    "ProjectDashboardSectionItemDescriptor",
    "ProjectDashboardSelectorOptionDescriptor",
    "ProjectDashboardSnapshotDescriptor",
    "ProjectManagementDashboardDesktopApi",
    "build_project_management_dashboard_desktop_api",
    "ProjectManagementWorkspaceDescriptor",
    "ProjectManagementWorkspaceDesktopApi",
    "build_project_management_workspace_desktop_api",
]
