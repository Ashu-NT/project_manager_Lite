from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class FinanceSetupFacts:
    project_id: str
    currency_code: str
    status: str
    billing_method: str
    budget_control_mode: str
    cost_code_policy: str
    financial_start_date: date | None
    financial_end_date: date | None
    is_funded: bool
    is_billable: bool
    default_cost_code: str
    version: int


__all__ = ["FinanceSetupFacts"]
