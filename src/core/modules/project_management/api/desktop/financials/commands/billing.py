from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class FinancialCreateBillingProfileCommand:
    project_id: str
    contract_reference: str
    contract_value: Decimal
    customer_party_id: str | None = None
    external_customer_reference: str | None = None
    purchase_order_reference: str | None = None
    cost_plus_markup_percent: Decimal = Decimal("0")
    payment_terms_days: int = 30
    retention_years: int = 7


@dataclass(frozen=True, slots=True)
class FinancialActivateBillingProfileCommand:
    project_id: str
    expected_version: int


@dataclass(frozen=True, slots=True)
class FinancialAddBillingScheduleLineCommand:
    project_id: str
    name: str
    amount: Decimal
    due_date: date
    task_id: str | None = None
    acceptance_reference: str | None = None


@dataclass(frozen=True, slots=True)
class FinancialMarkBillingScheduleLineReadyCommand:
    line_id: str
    expected_version: int


@dataclass(frozen=True, slots=True)
class FinancialCreateBillingPreparationCommand:
    project_id: str
    preparation_number: str
    period_start: date
    period_end: date
    idempotency_key: str
    correction_of_preparation_id: str | None = None


@dataclass(frozen=True, slots=True)
class FinancialAddFixedPriceBillingSourceCommand:
    preparation_id: str
    expected_version: int
    schedule_line_id: str


@dataclass(frozen=True, slots=True)
class FinancialAddApprovedTimeBillingSourceCommand:
    preparation_id: str
    expected_version: int
    time_entry_id: str


@dataclass(frozen=True, slots=True)
class FinancialAddCostPlusBillingSourceCommand:
    preparation_id: str
    expected_version: int
    cost_entry_id: str


@dataclass(frozen=True, slots=True)
class FinancialVersionedBillingPreparationCommand:
    preparation_id: str
    expected_version: int


__all__ = [
    "FinancialActivateBillingProfileCommand",
    "FinancialAddApprovedTimeBillingSourceCommand",
    "FinancialAddBillingScheduleLineCommand",
    "FinancialAddCostPlusBillingSourceCommand",
    "FinancialAddFixedPriceBillingSourceCommand",
    "FinancialCreateBillingPreparationCommand",
    "FinancialCreateBillingProfileCommand",
    "FinancialMarkBillingScheduleLineReadyCommand",
    "FinancialVersionedBillingPreparationCommand",
]
