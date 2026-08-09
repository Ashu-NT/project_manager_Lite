from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class FinancialCreateManualActualCommand:
    project_id: str
    command_id: str
    description: str
    amount: Decimal
    currency_code: str
    transaction_date: date
    cost_code_id: str
    entry_kind: str = "actual"
    task_id: str | None = None
    resource_id: str | None = None


@dataclass(frozen=True, slots=True)
class FinancialUpdateActualDraftCommand:
    entry_id: str
    expected_version: int
    description: str
    amount: Decimal
    currency_code: str
    transaction_date: date
    cost_code_id: str
    task_id: str | None = None
    resource_id: str | None = None


@dataclass(frozen=True, slots=True)
class FinancialVersionedActualCommand:
    entry_id: str
    expected_version: int


@dataclass(frozen=True, slots=True)
class FinancialDecideActualCommand:
    entry_id: str
    expected_version: int
    notes: str = ""


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


__all__ = [
    "FinancialCreateManualActualCommand",
    "FinancialDecideActualCommand",
    "FinancialPostActualCommand",
    "FinancialReverseActualCommand",
    "FinancialUpdateActualDraftCommand",
    "FinancialVersionedActualCommand",
]
