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
class EmployeeCreateCommand:
    # No lifecycle/user_id field -- every new Employee starts ACTIVE; System
    # Access is a separate relationship operation (link_employee_user_
    # account), never ordinary profile Create.
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


@dataclass(frozen=True)
class EmployeeUpdateCommand:
    # No lifecycle/user_id field -- see activate_employee/deactivate_
    # employee and link_employee_user_account/unlink_employee_user_account
    # on PlatformEmployeeDesktopApi instead.
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
    expected_version: int | None = None
