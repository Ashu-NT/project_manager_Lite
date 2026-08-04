from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DepartmentDto:
    id: str
    organization_id: str
    department_code: str
    name: str
    description: str
    site_id: str | None
    default_location_id: str | None
    parent_department_id: str | None
    department_type: str
    cost_center_code: str
    manager_employee_id: str | None
    is_active: bool
    notes: str
    version: int


@dataclass(frozen=True)
class DepartmentLocationReferenceDto:
    id: str
    organization_id: str
    site_id: str
    location_code: str
    name: str
    is_active: bool


@dataclass(frozen=True)
class DepartmentCreateCommand:
    department_code: str
    name: str
    description: str = ""
    site_id: str | None = None
    default_location_id: str | None = None
    parent_department_id: str | None = None
    department_type: str = ""
    cost_center_code: str = ""
    manager_employee_id: str | None = None
    is_active: bool = True
    notes: str = ""


@dataclass(frozen=True)
class DepartmentUpdateCommand:
    department_id: str
    department_code: str | None = None
    name: str | None = None
    description: str | None = None
    site_id: str | None = None
    default_location_id: str | None = None
    parent_department_id: str | None = None
    department_type: str | None = None
    cost_center_code: str | None = None
    manager_employee_id: str | None = None
    is_active: bool | None = None
    notes: str | None = None
    expected_version: int | None = None
