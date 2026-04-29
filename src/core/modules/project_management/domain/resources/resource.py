from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.src.core.modules.project_management.domain.enums import CostType, WorkerType
from src.src.core.modules.project_management.domain.identifiers import generate_id


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
    worker_type: WorkerType = WorkerType.EXTERNAL
    employee_id: Optional[str] = None

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
        worker_type: WorkerType = WorkerType.EXTERNAL,
        employee_id: str | None = None,
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
            worker_type=worker_type,
            employee_id=employee_id,
        )


__all__ = ["Resource"]


