"""Project management desktop API adapters."""

from src.core.modules.project_management.api.desktop.workspaces import (
    ProjectManagementWorkspaceDescriptor,
    ProjectManagementWorkspaceDesktopApi,
    build_project_management_workspace_desktop_api,
)

__all__ = [
    "ProjectManagementWorkspaceDescriptor",
    "ProjectManagementWorkspaceDesktopApi",
    "build_project_management_workspace_desktop_api",
]
