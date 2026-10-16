"""Dashboard desktop API — modular enterprise package."""

from src.core.modules.project_management.api.desktop.dashboard.api import (
    ProjectManagementDashboardDesktopApi,
)
from src.core.modules.project_management.api.desktop.dashboard.factories.dashboard_api_factory import (
    build_project_management_dashboard_desktop_api,
)

__all__ = [
    "ProjectManagementDashboardDesktopApi",
    "build_project_management_dashboard_desktop_api",
]
