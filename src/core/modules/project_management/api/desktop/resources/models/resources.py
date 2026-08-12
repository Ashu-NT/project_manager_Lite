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
    hourly_rate: str
    hourly_rate_label: str
    currency_code: str | None
    capacity_percent: float
    capacity_label: str
    address: str
    contact: str
    employee_id: str | None
    employee_context: str
    department: str
    site: str
    is_active: bool
    active_label: str
    version: int


@dataclass(frozen=True)
class ResourceCatalogPageDesktopDto:
    items: tuple[ResourceDesktopDto, ...] = ()
    filtered_total: int = 0
    total: int = 0
    active: int = 0
    employees: int = 0
    external: int = 0
    average_capacity: float = 0.0
    page: int = 1
    page_size: int = 25


__all__ = ["ResourceCatalogPageDesktopDto", "ResourceDesktopDto"]
