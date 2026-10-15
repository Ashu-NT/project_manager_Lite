from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class FinancialPostActualCommand:
    entry_id: str
    expected_version: int
    posting_date: date
    exchange_rate: Decimal | None = None
    exchange_rate_date: date | None = None
    exchange_rate_source: str | None = None
    exchange_rate_captured_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class FinancialReverseActualCommand:
    entry_id: str
    expected_version: int
    command_id: str
    posting_date: date
    reason: str


__all__ = ['FinancialPostActualCommand', 'FinancialReverseActualCommand']
