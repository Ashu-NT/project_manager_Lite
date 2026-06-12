from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from src.core.modules.project_management.domain.enums import CostType


@dataclass(frozen=True)
class FinancialUpdateCommand:
    cost_id: str
    description: str
    planned_amount: float
    task_id: str | None = None
    cost_type: str = CostType.OVERHEAD.value
    committed_amount: float = 0.0
    actual_amount: float = 0.0
    incurred_date: date | None = None
    currency_code: str | None = None
    expected_version: int | None = None
    code: str = ""


__all__ = ["FinancialUpdateCommand"]
