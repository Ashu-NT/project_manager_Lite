from __future__ import annotations

from dataclasses import dataclass


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
class FinancialRemoveDraftBillingLineCommand:
    preparation_id: str
    line_id: str
    expected_version: int


__all__ = ['FinancialAddFixedPriceBillingSourceCommand', 'FinancialAddApprovedTimeBillingSourceCommand', 'FinancialAddCostPlusBillingSourceCommand', 'FinancialRemoveDraftBillingLineCommand']
