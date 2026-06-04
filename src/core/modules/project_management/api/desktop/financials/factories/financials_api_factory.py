"""Factory for building the financials desktop API."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)


def build_project_management_financials_desktop_api(
    *,
    project_service=None,
    task_service=None,
    cost_service=None,
    finance_service=None,
    forecast_service=None,
    procurement_service=None,
    baseline_service=None,
) -> ProjectManagementFinancialsDesktopApi:
    return ProjectManagementFinancialsDesktopApi(
        project_service=project_service,
        task_service=task_service,
        cost_service=cost_service,
        finance_service=finance_service,
        forecast_service=forecast_service,
        procurement_service=procurement_service,
        baseline_service=baseline_service,
    )


__all__ = ["build_project_management_financials_desktop_api"]
