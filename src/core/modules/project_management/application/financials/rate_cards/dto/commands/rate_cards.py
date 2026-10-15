from __future__ import annotations

from dataclasses import dataclass


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
