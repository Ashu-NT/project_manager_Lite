from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.contracts.reads.financials.revenue.models.availability import (
    CommercialMetricAvailability,
    CommercialMetricUnavailableReason,
)


@dataclass(frozen=True, slots=True)
class FinancialCommercialProjectionDto:
    revenue_availability: CommercialMetricAvailability
    margin_availability: CommercialMetricAvailability
    percent_availability: CommercialMetricAvailability
    revenue_reason: CommercialMetricUnavailableReason | None
    margin_reason: CommercialMetricUnavailableReason | None
    percent_reason: CommercialMetricUnavailableReason | None

    project_id: str = ""
    project_currency: str = ""
    contract_value: str = ""
    approved_preparation_amount: str = "0"
    forecast_revenue_at_completion: str = ""
    revenue_basis: str = ""
    projected_margin_amount: str = ""
    projected_margin_percent: str = ""
    profitability_detail_included: bool = True
    as_of_date: str = ""
