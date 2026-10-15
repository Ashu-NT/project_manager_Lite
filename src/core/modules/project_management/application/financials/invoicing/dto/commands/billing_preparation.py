from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class FinancialCreateBillingPreparationCommand:
    project_id: str
    preparation_number: str
    period_start: date
    period_end: date
    idempotency_key: str
    correction_of_preparation_id: str | None = None


@dataclass(frozen=True, slots=True)
class FinancialVersionedBillingPreparationCommand:
    preparation_id: str
    expected_version: int


__all__ = ['FinancialCreateBillingPreparationCommand', 'FinancialVersionedBillingPreparationCommand']
