from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.domain.enums import CostType
from core.domain.identifiers import generate_id


@dataclass
class Resource:
    id: str
    name: str
    role: str = ""
    hourly_rate: float = 0.0
    is_active: bool = True
    cost_type: CostType = CostType.LABOR
    currency_code: Optional[str] = None
    version: int = 1

    @staticmethod
    def create(
        name: str,
        role: str = "",
        hourly_rate: float = 0.0,
        is_active: bool = True,
        cost_type: CostType = CostType.LABOR,
        currency_code: Optional[str] = None,
    ) -> "Resource":
        return Resource(
            id=generate_id(),
            name=name,
            role=role,
            hourly_rate=hourly_rate,
            is_active=is_active,
            cost_type=cost_type,
            currency_code=currency_code,
        )


__all__ = ["Resource"]
