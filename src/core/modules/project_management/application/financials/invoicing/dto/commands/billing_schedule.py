from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


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


__all__ = ['FinancialAddBillingScheduleLineCommand', 'FinancialMarkBillingScheduleLineReadyCommand']
