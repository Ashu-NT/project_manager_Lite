from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.modules.project_management.contracts.reads.sorting import ReadSort


@dataclass(frozen=True, slots=True)
class ResourceCatalogReadItem:
    resource: Resource
    employee_name: str = ""
    employee_title: str = ""
    employee_contact: str = ""
    department_label: str = ""
    site_label: str = ""


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
]
