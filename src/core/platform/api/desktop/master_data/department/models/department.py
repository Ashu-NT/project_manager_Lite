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
    manager_employee_id: str | None
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


@dataclass(frozen=True)
class DepartmentRollupSummaryDto:
    total: int
    active: int


@dataclass(frozen=True)
class DepartmentCreateCommand:
    """Lifecycle is not settable from Create -- every new department starts
    ACTIVE; use activate_department/deactivate_department instead."""

    department_code: str
    name: str
    description: str = ""
    site_id: str | None = None
    parent_department_id: str | None = None
    department_type: str = ""
    cost_center_code: str = ""
    manager_employee_id: str | None = None
    notes: str = ""


@dataclass(frozen=True)
class DepartmentUpdateCommand:
    """Pure profile update -- lifecycle is never settable from Edit; use
    activate_department/deactivate_department instead."""

    department_id: str
    department_code: str | None = None
    name: str | None = None
    description: str | None = None
    site_id: str | None = None
    parent_department_id: str | None = None
    department_type: str | None = None
    cost_center_code: str | None = None
    manager_employee_id: str | None = None
    notes: str | None = None
    expected_version: int | None = None
