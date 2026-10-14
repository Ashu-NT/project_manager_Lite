"""Factory for building the dashboard desktop API."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.dashboard.api import (
    ProjectManagementDashboardDesktopApi,
)


def build_project_management_dashboard_desktop_api(
    *,
    project_service=None,
    project_dashboard=None,
    portfolio_dashboard=None,
    baseline_query=None,
    earned_value_report=None,
    collaboration_inbox_query=None,
    approval_queries=None,
    task_workspace_query=None,
    module_catalog_service=None,
) -> ProjectManagementDashboardDesktopApi:
    return ProjectManagementDashboardDesktopApi(
        project_service=project_service,
        project_dashboard=project_dashboard,
        portfolio_dashboard=portfolio_dashboard,
        baseline_query=baseline_query,
        earned_value_report=earned_value_report,
        collaboration_inbox_query=collaboration_inbox_query,
        approval_queries=approval_queries,
        task_workspace_query=task_workspace_query,
        module_catalog_service=module_catalog_service,
    )


__all__ = ["build_project_management_dashboard_desktop_api"]
