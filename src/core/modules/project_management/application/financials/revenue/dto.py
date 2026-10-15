from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from src.core.modules.project_management.contracts.reads.financials.commercial_metric_availability import (
    CommercialMetricAvailability,
    CommercialMetricUnavailableReason,
)


@dataclass(frozen=True)
class ProjectCommercialProjection:
    """Contract and approved preparation amounts are managerial PM facts.

    forecast_revenue_at_completion/revenue_basis/
    projected_margin_* are further redacted without finance.read_profitability
    (profitability_detail_included is False, all four are None/"")."""

    project_id: str
    project_currency: str | None
    contract_value: Decimal | None
    approved_preparation_amount: Decimal
    forecast_revenue_at_completion: Decimal | None
    revenue_basis: str
    projected_margin_amount: Decimal | None
    projected_margin_percent: Decimal | None
    revenue_availability: CommercialMetricAvailability
    margin_availability: CommercialMetricAvailability
    percent_availability: CommercialMetricAvailability
    revenue_reason: CommercialMetricUnavailableReason | None
    margin_reason: CommercialMetricUnavailableReason | None
    percent_reason: CommercialMetricUnavailableReason | None
    tenant_id: str
    organization_id: str
    as_of_date: date
    profitability_detail_included: bool = True


__all__ = ['ProjectCommercialProjection']
