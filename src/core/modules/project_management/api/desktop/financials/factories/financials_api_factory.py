"""Factory for building the financials desktop API."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)


def build_project_management_financials_desktop_api(
    *,
    project_service=None,
    task_service=None,
    finance_service=None,
    baseline_service=None,
    finance_workspace_query=None,
    financial_configuration_service=None,
    cost_entry_service=None,
    commitment_service=None,
    forecast_version_service=None,
    financial_change_service=None,
    reporting_service=None,
) -> ProjectManagementFinancialsDesktopApi:
    return ProjectManagementFinancialsDesktopApi(
        project_service=project_service,
        task_service=task_service,
        finance_service=finance_service,
        baseline_service=baseline_service,
        finance_workspace_query=finance_workspace_query,
        financial_configuration_service=financial_configuration_service,
        cost_entry_service=cost_entry_service,
        commitment_service=commitment_service,
        forecast_version_service=forecast_version_service,
        financial_change_service=financial_change_service,
        reporting_service=reporting_service,
    )


__all__ = ["build_project_management_financials_desktop_api"]
