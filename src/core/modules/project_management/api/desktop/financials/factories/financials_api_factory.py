"""Factory for building the financials desktop API."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)


def build_project_management_financials_desktop_api(
    *,
    finance_snapshot_query=None,
    finance_workspace_query=None,
    finance_performance_query=None,
    finance_governance_commands=None,
    cost_entry_query=None,
    commitment_query=None,
    billing_profile_query=None,
    billing_preparation_query=None,
    report_sources=None,
    profitability_report=None,
) -> ProjectManagementFinancialsDesktopApi:
    return ProjectManagementFinancialsDesktopApi(
        finance_snapshot_query=finance_snapshot_query,
        finance_workspace_query=finance_workspace_query,
        finance_performance_query=finance_performance_query,
        finance_governance_commands=finance_governance_commands,
        cost_entry_query=cost_entry_query,
        commitment_query=commitment_query,
        billing_profile_query=billing_profile_query,
        billing_preparation_query=billing_preparation_query,
        report_sources=report_sources,
        profitability_report=profitability_report,
    )


__all__ = ["build_project_management_financials_desktop_api"]
