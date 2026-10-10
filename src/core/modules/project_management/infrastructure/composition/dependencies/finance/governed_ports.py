from __future__ import annotations

from typing import Literal

from src.core.modules.project_management.application.financials.governance import (
    FinanceGovernanceCommandBoundary,
    FinanceGovernedServicePort,
)

FinanceFamily = Literal[
    "financial_setup",
    "budget",
    "forecast_version",
    "forecast_generation",
    "financial_change",
    "rate_card",
    "planned_cost",
    "cost_entry",
    "billing_profile",
    "billing_preparation",
]

FINANCE_MUTATIONS: dict[FinanceFamily, frozenset[str]] = {
    "financial_setup": frozenset({
        "configure_profile", "transition_profile", "create_cost_code", "update_cost_code",
        "deactivate_cost_code", "activate_cost_code", "add_project_cost_code",
        "remove_project_cost_code",
    }),
    "budget": frozenset({
        "create_budget", "create_successor", "request_budget_approval", "submit_budget",
        "approve_budget", "reject_budget", "close_budget", "update_budget_header",
        "delete_budget", "add_line", "update_line", "delete_line",
    }),
    "forecast_version": frozenset({
        "create_forecast", "add_line", "update_line", "delete_line", "submit_forecast",
        "request_forecast_approval", "approve_forecast", "reject_forecast", "delete_forecast",
    }),
    "forecast_generation": frozenset({"generate_draft"}),
    "financial_change": frozenset({
        "create_change", "update_change", "add_impact", "update_impact",
        "remove_impact", "submit_change",
    }),
    "rate_card": frozenset({
        "create_rate_card", "update_rate_card", "deactivate_rate_card", "create_line",
        "update_line", "deactivate_line",
    }),
    "planned_cost": frozenset({"calculate_snapshot"}),
    "cost_entry": frozenset({
        "create_manual_entry", "update_draft", "delete_draft", "submit", "approve",
        "reject", "post", "reverse",
    }),
    "billing_profile": frozenset({
        "create_profile", "activate_profile", "add_schedule_line", "mark_schedule_line_ready",
    }),
    "billing_preparation": frozenset({
        "create_preparation", "add_fixed_price_source", "add_approved_time_source",
        "add_cost_plus_source", "remove_draft_line", "cancel_draft_preparation",
        "submit_preparation", "request_delivery",
    }),
}


def wrap_finance_service(
    read_service: object,
    boundary: FinanceGovernanceCommandBoundary,
    *,
    family: FinanceFamily,
) -> FinanceGovernedServicePort:
    return FinanceGovernedServicePort(
        read_service=read_service,
        boundary=boundary,
        family=family,
        mutations=FINANCE_MUTATIONS[family],
    )
