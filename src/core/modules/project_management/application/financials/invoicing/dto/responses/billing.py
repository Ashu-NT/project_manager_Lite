from __future__ import annotations

from dataclasses import dataclass
from datetime import date


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
class FinancialBillingPreparationResponse:
    id: str
    project_id: str
    preparation_number: str
    billing_method: str
    status: str
    period_start: date
    period_end: date
    line_count: int
    total_amount: str
    currency_code: str
    row_version: int
