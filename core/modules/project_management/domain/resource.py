from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.modules.project_management.domain.enums import CostType
from core.modules.project_management.domain.identifiers import generate_id


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
    capacity_percent: float = 100.0
    address: str = ""
    contact: str = ""

    @staticmethod
    def create(
        name: str,
        role: str = "",
        hourly_rate: float = 0.0,
        is_active: bool = True,
        cost_type: CostType = CostType.LABOR,
        currency_code: Optional[str] = None,
        capacity_percent: float = 100.0,
        address: str = "",
        contact: str = "",
    ) -> "Resource":
        return Resource(
            id=generate_id(),
            name=name,
            role=role,
            hourly_rate=hourly_rate,
            is_active=is_active,
            cost_type=cost_type,
            currency_code=currency_code,
            capacity_percent=capacity_percent,
            address=address,
            contact=contact,
        )


__all__ = ["Resource"]
