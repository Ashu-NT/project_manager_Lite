"""Commercial read-contract enums, separate from immutable fact dataclasses."""

from enum import StrEnum


class CommercialMetricAvailability(StrEnum):
    AVAILABLE = "available"
    NOT_CONFIGURED = "not_configured"
    UNSUPPORTED = "unsupported"
    UNAVAILABLE = "unavailable"
    RESTRICTED = "restricted"
    NOT_APPLICABLE = "not_applicable"


class CommercialMetricUnavailableReason(StrEnum):
    BILLING_PROFILE_MISSING = "billing_profile_missing"
    FINANCIAL_PROFILE_MISSING = "financial_profile_missing"
    CONTRACT_VALUE_MISSING = "contract_value_missing"
    EAC_UNAVAILABLE = "eac_unavailable"
    T_AND_M_FORECAST_AUTHORITY_MISSING = "t_and_m_forecast_authority_missing"
    RECOVERABLE_COST_AUTHORITY_MISSING = "recoverable_cost_authority_missing"
    ZERO_DENOMINATOR = "zero_denominator"
    NON_BILLABLE = "non_billable"
    CURRENCY_MISMATCH = "currency_mismatch"
    PROFITABILITY_PERMISSION_REQUIRED = "profitability_permission_required"
    QUERY_NOT_CONNECTED = "query_not_connected"
    PROJECT_NOT_SELECTED = "project_not_selected"
