from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.contracts.reads.financials.models.commercial_metric_availability import (
    CommercialMetricAvailability,
    CommercialMetricUnavailableReason,
)


@dataclass(frozen=True, slots=True)
class FinancialBillingProfileDto:
    id: str = ""
    status: str = ""
    currency_code: str = ""
    contract_reference: str = ""
    contract_value: str = "0"
    customer_party_id: str = ""
    external_customer_reference: str = ""
    purchase_order_reference: str = ""
    payment_terms_days: int = 0
    row_version: int = 1


@dataclass(frozen=True, slots=True)
class FinancialBillingScheduleLineDto:
    id: str
    name: str
    status: str
    amount: str
    currency_code: str
    due_date: str
    task_id: str = ""
    acceptance_reference: str = ""
    row_version: int = 1


@dataclass(frozen=True, slots=True)
class FinancialBillingPreparationDto:
    id: str
    preparation_number: str
    billing_method: str
    status: str
    period_label: str
    line_count: int
    total_amount: str
    currency_code: str
    external_system: str = ""
    external_status: str = ""
    external_invoice_reference: str = ""
    reconciliation_reference: str = ""
    row_version: int = 1


@dataclass(frozen=True, slots=True)
class FinancialBillingPreparationLineDto:
    id: str
    preparation_id: str
    source_type: str
    source_id: str
    description: str
    source_date: str
    quantity: str
    unit: str
    unit_rate: str
    net_amount: str
    currency_code: str
    task_id: str = ""
    resource_id: str = ""


@dataclass(frozen=True, slots=True)
class FinancialBillingSourceOptionDto:
    source_id: str
    source_type: str
    label: str
    source_date: str
    amount: str
    currency_code: str


@dataclass(frozen=True, slots=True)
class FinancialBillingSourcePageDto:
    items: tuple[FinancialBillingSourceOptionDto, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 50
    sort_key: str = "source_date"
    sort_direction: str = "asc"


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


__all__ = [
    "FinancialBillingPreparationDto",
    "FinancialBillingPreparationLineDto",
    "FinancialBillingProfileDto",
    "FinancialBillingScheduleLineDto",
    "FinancialBillingSourceOptionDto",
    "FinancialBillingSourcePageDto",
    "FinancialCommercialProjectionDto",
]
