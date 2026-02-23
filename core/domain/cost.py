from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from core.domain.enums import CostType
from core.domain.identifiers import generate_id


@dataclass
class CostItem:
    id: str
    project_id: str
    task_id: Optional[str]
    description: str
    planned_amount: float
    cost_type: CostType = CostType.OVERHEAD
    committed_amount: float = 0.0
    actual_amount: float = 0.0
    incurred_date: Optional[date] = None
    currency_code: Optional[str] = None

    @staticmethod
    def create(
        project_id: str,
        description: str,
        planned_amount: float,
        task_id: Optional[str] = None,
        cost_type: CostType = CostType.OVERHEAD,
        committed_amount: float = 0.0,
        actual_amount: float = 0.0,
        incurred_date: Optional[date] = None,
        currency_code: Optional[str] = None,
    ) -> "CostItem":
        return CostItem(
            id=generate_id(),
            project_id=project_id,
            task_id=task_id,
            description=description,
            planned_amount=planned_amount,
            cost_type=cost_type,
            committed_amount=committed_amount,
            actual_amount=actual_amount,
            incurred_date=incurred_date,
            currency_code=currency_code,
        )


__all__ = ["CostItem"]
