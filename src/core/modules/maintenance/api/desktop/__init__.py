"""Maintenance desktop API adapters."""

from src.core.modules.maintenance.api.desktop.workspaces import (
    MaintenanceWorkspaceDescriptor,
    MaintenanceWorkspaceDesktopApi,
    build_maintenance_workspace_desktop_api,
)

__all__ = [
    "MaintenanceWorkspaceDescriptor",
    "MaintenanceWorkspaceDesktopApi",
    "build_maintenance_workspace_desktop_api",
]
