from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.platform.org.domain import Employee, EmploymentType, Organization
    from core.platform.org.service import EmployeeService, OrganizationService

__all__ = ["Employee", "EmployeeService", "EmploymentType", "Organization", "OrganizationService"]


def __getattr__(name: str):
    if name == "Employee":
        from core.platform.org.domain import Employee

        return Employee
    if name == "EmploymentType":
        from core.platform.org.domain import EmploymentType

        return EmploymentType
    if name == "Organization":
        from core.platform.org.domain import Organization

        return Organization
    if name == "EmployeeService":
        from core.platform.org.service import EmployeeService

        return EmployeeService
    if name == "OrganizationService":
        from core.platform.org.service import OrganizationService

        return OrganizationService
    raise AttributeError(name)
