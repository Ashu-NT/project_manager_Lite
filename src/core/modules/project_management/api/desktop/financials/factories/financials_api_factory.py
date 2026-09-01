"""Factory for building the financials desktop API."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)


def build_project_management_financials_desktop_api(
    *,
    finance_service=None,
    finance_workspace_query=None,
    finance_performance_query=None,
    finance_governance_commands=None,
    financial_configuration_service=None,
    cost_entry_service=None,
    commitment_service=None,
    billing_profile_service=None,
    billing_preparation_service=None,
    reporting_service=None,
) -> ProjectManagementFinancialsDesktopApi:
    return ProjectManagementFinancialsDesktopApi(
        finance_service=finance_service,
        finance_workspace_query=finance_workspace_query,
        finance_performance_query=finance_performance_query,
        finance_governance_commands=finance_governance_commands,
        financial_configuration_service=financial_configuration_service,
        cost_entry_service=cost_entry_service,
        commitment_service=commitment_service,
        billing_profile_service=billing_profile_service,
        billing_preparation_service=billing_preparation_service,
        reporting_service=reporting_service,
    )


__all__ = ["build_project_management_financials_desktop_api"]
