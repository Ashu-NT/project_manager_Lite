from __future__ import annotations

from dataclasses import dataclass, field


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
class FinancialBillingWorkspaceDto:
    profile: FinancialBillingProfileDto = field(default_factory=FinancialBillingProfileDto)
    schedule_lines: tuple[FinancialBillingScheduleLineDto, ...] = field(default_factory=tuple)
    preparations: tuple[FinancialBillingPreparationDto, ...] = field(default_factory=tuple)
    preparation_page: int = 1
    preparation_page_size: int = 50
    preparation_total: int = 0


@dataclass(frozen=True, slots=True)
class FinancialCommercialProjectionDto:
    """ADR-PF-010's five commercial projections. contract_value/billable_amount/
    externally_invoiced_amount/externally_paid_amount require only finance.read;
    forecast_revenue_at_completion/revenue_basis/projected_margin_amount/
    projected_margin_percent require finance.read_profitability and are blank
    (profitability_detail_included=False) otherwise."""

    project_id: str = ""
    project_currency: str = ""
    contract_value: str = ""
    billable_amount: str = "0"
    externally_invoiced_amount: str = "0"
    externally_paid_amount: str = "0"
    external_accounting_data_available: bool = False
    forecast_revenue_at_completion: str = ""
    revenue_basis: str = ""
    projected_margin_amount: str = ""
    projected_margin_percent: str = ""
    profitability_detail_included: bool = True


__all__ = [
    "FinancialBillingPreparationDto",
    "FinancialBillingPreparationLineDto",
    "FinancialBillingProfileDto",
    "FinancialBillingScheduleLineDto",
    "FinancialBillingWorkspaceDto",
    "FinancialCommercialProjectionDto",
]
