"""Factory for building the dashboard desktop API."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.dashboard.api import (
    ProjectManagementDashboardDesktopApi,
)


def build_project_management_dashboard_desktop_api(
    *,
    project_service=None,
    dashboard_service=None,
    baseline_service=None,
    reporting_service=None,
    register_service=None,
    collaboration_service=None,
    approval_service=None,
) -> ProjectManagementDashboardDesktopApi:
    return ProjectManagementDashboardDesktopApi(
        project_service=project_service,
        dashboard_service=dashboard_service,
        baseline_service=baseline_service,
        reporting_service=reporting_service,
        register_service=register_service,
        collaboration_service=collaboration_service,
        approval_service=approval_service,
    )


__all__ = ["build_project_management_dashboard_desktop_api"]
