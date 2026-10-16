from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.core.modules.project_management.domain.enums import (
    CostType,
    ResourceKind,
    WorkerType,
)


@dataclass(frozen=True, slots=True)
class ResourceResponse:
    id: str
    name: str
    kind: ResourceKind = ResourceKind.PERSON
    code: str = ""
    role: str = ""
    hourly_rate: Decimal = Decimal(0)
    is_active: bool = True
    cost_type: CostType = CostType.LABOR
    currency_code: str | None = None
    version: int = 1
    capacity_percent: float = 100.0
    address: str = ""
    contact: str = ""
    worker_type: WorkerType = WorkerType.EXTERNAL
    employee_id: str | None = None
    organization_id: str | None = None
    department_id: str | None = None
    site_id: str | None = None










