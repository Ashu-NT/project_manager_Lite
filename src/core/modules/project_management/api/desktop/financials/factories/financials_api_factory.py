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
    cost_entry_service=None,
    commitment_service=None,
    billing_profile_service=None,
    billing_preparation_service=None,
    report_sources=None,
    profitability_report=None,
) -> ProjectManagementFinancialsDesktopApi:
    return ProjectManagementFinancialsDesktopApi(
        finance_service=finance_service,
        finance_workspace_query=finance_workspace_query,
        finance_performance_query=finance_performance_query,
        finance_governance_commands=finance_governance_commands,
        cost_entry_service=cost_entry_service,
        commitment_service=commitment_service,
        billing_profile_service=billing_profile_service,
        billing_preparation_service=billing_preparation_service,
        report_sources=report_sources,
        profitability_report=profitability_report,
    )


__all__ = ["build_project_management_financials_desktop_api"]
