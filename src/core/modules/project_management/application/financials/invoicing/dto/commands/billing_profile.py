from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class FinancialCreateBillingProfileCommand:
    project_id: str
    contract_reference: str
    contract_value: Decimal
    customer_party_id: str | None = None
    external_customer_reference: str | None = None
    purchase_order_reference: str | None = None
    cost_plus_markup_percent: Decimal = Decimal(0)
    payment_terms_days: int = 30
    retention_years: int = 7


@dataclass(frozen=True, slots=True)
class FinancialActivateBillingProfileCommand:
    project_id: str
    expected_version: int


__all__ = ['FinancialCreateBillingProfileCommand', 'FinancialActivateBillingProfileCommand']
