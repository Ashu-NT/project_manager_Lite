from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmployeeDto:
    id: str
    employee_code: str
    full_name: str
    department_id: str | None
    department: str
    site_id: str | None
    site_name: str
    title: str
    employment_type: str
    email: str | None
    phone: str | None
    is_active: bool
    version: int


@dataclass(frozen=True)
class EmployeeCreateCommand:
    employee_code: str
    full_name: str
    department_id: str | None = None
    department: str = ""
    site_id: str | None = None
    site_name: str = ""
    title: str = ""
    employment_type: str = "FULL_TIME"
    email: str | None = None
    phone: str | None = None
    is_active: bool = True


@dataclass(frozen=True)
class EmployeeUpdateCommand:
    employee_id: str
    employee_code: str | None = None
    full_name: str | None = None
    department_id: str | None = None
    department: str | None = None
    site_id: str | None = None
    site_name: str | None = None
    title: str | None = None
    employment_type: str | None = None
    email: str | None = None
    phone: str | None = None
    is_active: bool | None = None
    expected_version: int | None = None
