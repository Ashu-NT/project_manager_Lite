from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.modules.project_management.domain.identifiers import generate_id


class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    TEMPORARY = "TEMPORARY"


@dataclass
class Organization:
    id: str
    organization_code: str
    display_name: str
    timezone_name: str = "UTC"
    base_currency: str = "EUR"
    is_active: bool = True
    version: int = 1

    @staticmethod
    def create(
        organization_code: str,
        display_name: str,
        timezone_name: str = "UTC",
        base_currency: str = "EUR",
        is_active: bool = True,
    ) -> "Organization":
        return Organization(
            id=generate_id(),
            organization_code=organization_code,
            display_name=display_name,
            timezone_name=timezone_name,
            base_currency=base_currency,
            is_active=is_active,
            version=1,
        )


@dataclass
class Site:
    id: str
    organization_id: str
    site_code: str
    display_name: str
    is_active: bool = True
    version: int = 1

    @staticmethod
    def create(
        organization_id: str,
        site_code: str,
        display_name: str,
        *,
        is_active: bool = True,
    ) -> "Site":
        return Site(
            id=generate_id(),
            organization_id=organization_id,
            site_code=site_code,
            display_name=display_name,
            is_active=is_active,
            version=1,
        )


@dataclass
class Department:
    id: str
    organization_id: str
    department_code: str
    display_name: str
    is_active: bool = True
    version: int = 1

    @staticmethod
    def create(
        organization_id: str,
        department_code: str,
        display_name: str,
        *,
        is_active: bool = True,
    ) -> "Department":
        return Department(
            id=generate_id(),
            organization_id=organization_id,
            department_code=department_code,
            display_name=display_name,
            is_active=is_active,
            version=1,
        )


@dataclass
class Employee:
    id: str
    employee_code: str
    full_name: str
    department: str = ""
    site_name: str = ""
    title: str = ""
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True
    version: int = 1

    @staticmethod
    def create(
        employee_code: str,
        full_name: str,
        department: str = "",
        site_name: str = "",
        title: str = "",
        employment_type: EmploymentType = EmploymentType.FULL_TIME,
        email: str | None = None,
        phone: str | None = None,
        is_active: bool = True,
    ) -> "Employee":
        return Employee(
            id=generate_id(),
            employee_code=employee_code,
            full_name=full_name,
            department=department,
            site_name=site_name,
            title=title,
            employment_type=employment_type,
            email=email,
            phone=phone,
            is_active=is_active,
            version=1,
        )

__all__ = ["Department", "Employee", "EmploymentType", "Organization", "Site"]
