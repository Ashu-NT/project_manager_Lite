from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.domain.enums import CostType, WorkerType


@dataclass(frozen=True)
class ResourceCreateCommand:
    name: str = ""
    code: str = ""
    role: str = ""
    hourly_rate: float = 0.0
    is_active: bool = True
    cost_type: str = CostType.LABOR.value
    currency_code: str | None = None
    capacity_percent: float = 100.0
    address: str = ""
    contact: str = ""
    worker_type: str = WorkerType.EXTERNAL.value
    employee_id: str | None = None


@dataclass(frozen=True)
class ResourceUpdateCommand:
    resource_id: str
    name: str = ""
    code: str = ""
    role: str = ""
    hourly_rate: float = 0.0
    is_active: bool = True
    cost_type: str = CostType.LABOR.value
    currency_code: str | None = None
    capacity_percent: float = 100.0
    address: str = ""
    contact: str = ""
    worker_type: str = WorkerType.EXTERNAL.value
    employee_id: str | None = None
    expected_version: int | None = None


__all__ = ["ResourceCreateCommand", "ResourceUpdateCommand"]
