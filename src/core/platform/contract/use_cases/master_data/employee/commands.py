"""Transport-neutral employee use-case commands (desktop and future HTTP adapters)."""

from __future__ import annotations

from dataclasses import dataclass


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


__all__ = [
    "EmployeeCreateCommand",
    "EmployeeUpdateCommand",
]
