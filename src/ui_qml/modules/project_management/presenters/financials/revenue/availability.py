"""Presentation labels for server-authored commercial availability."""

from src.core.modules.project_management.api.desktop.financials.models.billing import (
    CommercialMetricAvailability,
    CommercialMetricUnavailableReason,
)


def availability_label(
    value: CommercialMetricAvailability,
    reason: CommercialMetricUnavailableReason | None = None,
) -> str:
    if value is CommercialMetricAvailability.UNAVAILABLE:
        return {
            CommercialMetricUnavailableReason.EAC_UNAVAILABLE: "Canonical EAC unavailable",
            CommercialMetricUnavailableReason.CURRENCY_MISMATCH: "Unavailable: currency mismatch",
            CommercialMetricUnavailableReason.QUERY_NOT_CONNECTED: "Commercial query unavailable",
            CommercialMetricUnavailableReason.PROJECT_NOT_SELECTED: "Select a project",
        }.get(reason, "Unavailable")
    return {
        "available": "Available",
        "restricted": "Restricted",
        "not_configured": "Not configured",
        "unsupported": "Projection unavailable for this billing method",
        "not_applicable": "Not applicable",
    }.get(value, "Unavailable")


def reason_label(reason: CommercialMetricUnavailableReason | None) -> str:
    return {
        CommercialMetricUnavailableReason.BILLING_PROFILE_MISSING: "Billing profile is not configured.",
        CommercialMetricUnavailableReason.FINANCIAL_PROFILE_MISSING: "Financial profile is not configured.",
        CommercialMetricUnavailableReason.CONTRACT_VALUE_MISSING: "Contract value is not configured.",
        CommercialMetricUnavailableReason.EAC_UNAVAILABLE: "An authoritative cost estimate at completion is required.",
        CommercialMetricUnavailableReason.T_AND_M_FORECAST_AUTHORITY_MISSING: "No governed future billable-volume authority exists for T&M.",
        CommercialMetricUnavailableReason.RECOVERABLE_COST_AUTHORITY_MISSING: "No governed forecast recoverable-cost authority exists for Cost-Plus.",
        CommercialMetricUnavailableReason.ZERO_DENOMINATOR: "Percentage is not applicable when projected commercial revenue is zero.",
        CommercialMetricUnavailableReason.NON_BILLABLE: "The project is non-billable.",
        CommercialMetricUnavailableReason.CURRENCY_MISMATCH: "Commercial and cost currencies must match; no currency conversion is performed.",
        CommercialMetricUnavailableReason.PROFITABILITY_PERMISSION_REQUIRED: "Profitability permission is required.",
        CommercialMetricUnavailableReason.QUERY_NOT_CONNECTED: "The commercial query is not connected.",
        CommercialMetricUnavailableReason.PROJECT_NOT_SELECTED: "Select a project.",
        None: "",
    }[reason]
