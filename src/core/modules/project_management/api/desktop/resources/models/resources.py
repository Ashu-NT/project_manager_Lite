from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceDesktopDto:
    id: str
    name: str
    code: str
    role: str
    worker_type: str
    worker_type_label: str
    cost_type: str
    cost_type_label: str
    hourly_rate: float
    hourly_rate_label: str
    currency_code: str | None
    capacity_percent: float
    capacity_label: str
    address: str
    contact: str
    employee_id: str | None
    employee_context: str
    is_active: bool
    active_label: str
    version: int


__all__ = ["ResourceDesktopDto"]
