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
class FinancialBillingWorkspaceDto:
    profile: FinancialBillingProfileDto = field(default_factory=FinancialBillingProfileDto)
    schedule_lines: tuple[FinancialBillingScheduleLineDto, ...] = field(default_factory=tuple)
    preparations: tuple[FinancialBillingPreparationDto, ...] = field(default_factory=tuple)
    preparation_page: int = 1
    preparation_page_size: int = 50
    preparation_total: int = 0


__all__ = [
    "FinancialBillingPreparationDto",
    "FinancialBillingProfileDto",
    "FinancialBillingScheduleLineDto",
    "FinancialBillingWorkspaceDto",
]
