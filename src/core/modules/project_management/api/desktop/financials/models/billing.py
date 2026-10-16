from __future__ import annotations

from dataclasses import dataclass


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


__all__ = [
    "FinancialBillingPreparationDto",
    "FinancialBillingSourceOptionDto",
    "FinancialBillingSourcePageDto",
]
