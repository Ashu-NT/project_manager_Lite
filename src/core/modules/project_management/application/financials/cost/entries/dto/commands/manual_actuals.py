from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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


__all__ = ['FinancialCreateManualActualCommand', 'FinancialUpdateActualDraftCommand', 'FinancialVersionedActualCommand']
