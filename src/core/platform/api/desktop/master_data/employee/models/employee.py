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
    # `status` ("active"/"inactive") is the real, sole lifecycle source of
    # truth -- `is_active` is a derived read convenience computed once at
    # serialization time (see PlatformEmployeeDesktopApi._serialize), never
    # a second independently-settable value.
    status: str
    is_active: bool
    version: int
    user_id: str | None = None
    organization_id: str | None = None


@dataclass(frozen=True)
class EmployeePageDto:
    items: tuple[EmployeeDto, ...] = ()
    total: int = 0
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25


@dataclass(frozen=True)
class EmployeeHeadcountSummaryDto:
    total: int
    active: int


@dataclass(frozen=True)
class EmployeeDepartmentBreakdownRowDto:
    department_id: str | None
    department_name: str
    total: int
    active: int


@dataclass(frozen=True)
class EmployeeSiteBreakdownRowDto:
    site_id: str | None
    site_name: str
    total: int
    active: int


