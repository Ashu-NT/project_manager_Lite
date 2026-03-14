from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.platform.org.domain import Employee, EmploymentType
    from core.platform.org.service import EmployeeService

__all__ = ["Employee", "EmployeeService", "EmploymentType"]


def __getattr__(name: str):
    if name == "Employee":
        from core.platform.org.domain import Employee

        return Employee
    if name == "EmploymentType":
        from core.platform.org.domain import EmploymentType

        return EmploymentType
    if name == "EmployeeService":
        from core.platform.org.service import EmployeeService

        return EmployeeService
    raise AttributeError(name)
