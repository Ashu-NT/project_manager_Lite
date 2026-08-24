from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from src.core.modules.project_management.contracts.reads.sorting import ReadSort


@dataclass(frozen=True, slots=True)
class ResourceCatalogReadItem:
    resource_id: str
    code: str
    name: str
    role: str
    worker_type: str
    cost_type: str
    is_active: bool
    capacity_percent: float
    organization_id: str
    organization_label: str = ""
    department_id: str | None = None
    employee_name: str = ""
    employee_title: str = ""
    department_label: str = ""
    site_id: str | None = None
    site_label: str = ""
    employee_id: str | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class ResourceInspectorFact:
    resource_id: str
    code: str
    name: str
    role: str
    worker_type: str
    is_active: bool
    capacity_percent: float
    organization_id: str
    organization_label: str = ""
    department_id: str | None = None
    department_label: str = ""
    site_id: str | None = None
    site_label: str = ""
    employee_id: str | None = None
    employee_name: str = ""
    project_count: int = 0
    assignment_count: int = 0
    version: int = 1
    can_read: bool = False
    can_manage: bool = False
    can_deactivate: bool = False
    can_reactivate: bool = False


@dataclass(frozen=True, slots=True)
class ResourceSummaryFact:
    resource_id: str
    code: str
    name: str
    role: str
    worker_type: str
    cost_type: str
    hourly_rate: Decimal
    currency_code: str | None
    is_active: bool
    capacity_percent: float
    address: str
    contact: str
    organization_id: str
    organization_label: str = ""
    department_id: str | None = None
    department_label: str = ""
    site_id: str | None = None
    site_label: str = ""
    employee_id: str | None = None
    employee_name: str = ""
    employee_title: str = ""
    version: int = 1
    can_read: bool = False
    can_manage: bool = False


@dataclass(frozen=True, slots=True)
class ResourceCatalogSummary:
    total: int = 0
    active: int = 0
    employees: int = 0
    external: int = 0
    average_capacity: float = 0.0


@dataclass(frozen=True, slots=True)
class ResourceCatalogReadPage:
    items: tuple[ResourceCatalogReadItem, ...] = ()
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25
    summary: ResourceCatalogSummary = ResourceCatalogSummary()
    sort: ReadSort = ReadSort("catalog")


__all__ = [
    "ResourceCatalogReadItem",
    "ResourceCatalogReadPage",
    "ResourceCatalogSummary",
    "ResourceInspectorFact",
    "ResourceSummaryFact",
]
