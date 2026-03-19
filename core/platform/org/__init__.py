from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.platform.org.domain import Department, Employee, EmploymentType, Organization, Site
    from core.platform.org.service import DepartmentService, EmployeeService, OrganizationService, SiteService

__all__ = [
    "Department",
    "DepartmentService",
    "Employee",
    "EmployeeService",
    "EmploymentType",
    "Organization",
    "OrganizationService",
    "Site",
    "SiteService",
]


def __getattr__(name: str):
    if name == "Department":
        from core.platform.org.domain import Department

        return Department
    if name == "Employee":
        from core.platform.org.domain import Employee

        return Employee
    if name == "EmploymentType":
        from core.platform.org.domain import EmploymentType

        return EmploymentType
    if name == "Organization":
        from core.platform.org.domain import Organization

        return Organization
    if name == "Site":
        from core.platform.org.domain import Site

        return Site
    if name == "EmployeeService":
        from core.platform.org.service import EmployeeService

        return EmployeeService
    if name == "OrganizationService":
        from core.platform.org.service import OrganizationService

        return OrganizationService
    if name == "DepartmentService":
        from core.platform.org.service import DepartmentService

        return DepartmentService
    if name == "SiteService":
        from core.platform.org.service import SiteService

        return SiteService
    raise AttributeError(name)
