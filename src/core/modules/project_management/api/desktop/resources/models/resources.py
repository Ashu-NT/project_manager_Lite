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
class ResourceCatalogItemDesktopDto:
    id: str
    code: str
    name: str
    role: str
    worker_type: str
    worker_type_label: str
    cost_type: str
    cost_type_label: str
    organization_id: str
    organization_label: str
    department_id: str | None
    department: str
    site_id: str | None
    site: str
    employee_id: str | None
    employee_name: str
    is_active: bool
    active_label: str
    capacity_percent: float
    capacity_label: str
    version: int


@dataclass(frozen=True)
class ResourceInspectorDesktopDto:
    id: str
    code: str
    name: str
    role: str
    worker_type: str
    worker_type_label: str
    organization_id: str
    organization_label: str
    department_id: str | None
    department: str
    site_id: str | None
    site: str
    employee_id: str | None
    employee_name: str
    is_active: bool
    active_label: str
    capacity_percent: float
    capacity_label: str
    project_count: int
    assignment_count: int
    version: int
    can_read: bool
    can_manage: bool
    can_deactivate: bool
    can_reactivate: bool


@dataclass(frozen=True)
class ResourceSummaryDesktopDto:
    id: str
    code: str
    name: str
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
    organization_id: str
    organization_label: str
    department_id: str | None
    department: str
    site_id: str | None
    site: str
    employee_id: str | None
    employee_name: str
    employee_title: str
    employee_context: str
    is_active: bool
    active_label: str
    version: int
    can_read: bool
    can_manage: bool


@dataclass(frozen=True)
class ResourceCatalogPageDesktopDto:
    items: tuple[ResourceCatalogItemDesktopDto, ...] = ()
    filtered_total: int = 0
    total: int = 0
    active: int = 0
    employees: int = 0
    external: int = 0
    average_capacity: float = 0.0
    page: int = 1
    page_size: int = 25
    sort_key: str = "catalog"
    sort_direction: str = "asc"


__all__ = [
    "ResourceCatalogItemDesktopDto",
    "ResourceCatalogPageDesktopDto",
    "ResourceDesktopDto",
    "ResourceInspectorDesktopDto",
    "ResourceSummaryDesktopDto",
]
