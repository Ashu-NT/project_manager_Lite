from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DepartmentDto:
    id: str
    organization_id: str
    department_code: str
    name: str
    description: str
    site_id: str | None
    parent_department_id: str | None
    department_type: str
    cost_center_code: str
    head_of_department_employee_id: str | None
    is_active: bool
    notes: str
    version: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class DepartmentPageDto:
    items: tuple[DepartmentDto, ...] = ()
    total: int = 0
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25




