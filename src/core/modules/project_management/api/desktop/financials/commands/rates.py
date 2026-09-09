from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class FinancialCreateRateCardCommand:
    name: str
    project_id: str | None = None


@dataclass(frozen=True, slots=True)
class FinancialUpdateRateCardCommand:
    rate_card_id: str
    expected_version: int
    name: str


@dataclass(frozen=True, slots=True)
class FinancialVersionedRateCardCommand:
    rate_card_id: str
    expected_version: int


@dataclass(frozen=True, slots=True)
class FinancialAddRateLineCommand:
    rate_card_id: str
    expected_card_version: int
    rate_type: str
    unit: str
    rate_amount: str
    rate_currency: str
    resource_id: str | None = None
    customer_party_id: str | None = None
    contract_reference: str | None = None
    role: str | None = None
    skill_code: str | None = None
    department_id: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    overtime_multiplier: str | None = None
    weekend_multiplier: str | None = None
    holiday_multiplier: str | None = None


@dataclass(frozen=True, slots=True)
class FinancialUpdateRateLineCommand:
    rate_line_id: str
    expected_version: int
    expected_card_version: int
    rate_amount: str
    effective_from: date | None = None
    effective_to: date | None = None
    overtime_multiplier: str | None = None
    weekend_multiplier: str | None = None
    holiday_multiplier: str | None = None


@dataclass(frozen=True, slots=True)
class FinancialVersionedRateLineCommand:
    rate_line_id: str
    expected_version: int
    expected_card_version: int


__all__ = [
    "FinancialAddRateLineCommand",
    "FinancialCreateRateCardCommand",
    "FinancialUpdateRateCardCommand",
    "FinancialUpdateRateLineCommand",
    "FinancialVersionedRateCardCommand",
    "FinancialVersionedRateLineCommand",
]
