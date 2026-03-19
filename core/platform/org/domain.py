from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone as dt_timezone
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
    name: str
    description: str = ""
    country: str = ""
    region: str = ""
    city: str = ""
    address_line_1: str = ""
    address_line_2: str = ""
    postal_code: str = ""
    timezone: str = ""
    currency_code: str = ""
    site_type: str = ""
    status: str = "ACTIVE"
    default_calendar_id: str = ""
    default_language: str = ""
    is_active: bool = True
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        organization_id: str,
        site_code: str,
        name: str,
        *,
        description: str = "",
        country: str = "",
        region: str = "",
        city: str = "",
        address_line_1: str = "",
        address_line_2: str = "",
        postal_code: str = "",
        timezone: str = "",
        currency_code: str = "",
        site_type: str = "",
        status: str = "ACTIVE",
        default_calendar_id: str = "",
        default_language: str = "",
        is_active: bool = True,
        opened_at: datetime | None = None,
        closed_at: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        notes: str = "",
    ) -> "Site":
        now = datetime.now(dt_timezone.utc)
        return Site(
            id=generate_id(),
            organization_id=organization_id,
            site_code=site_code,
            name=name,
            description=description,
            country=country,
            region=region,
            city=city,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            postal_code=postal_code,
            timezone=timezone,
            currency_code=currency_code,
            site_type=site_type,
            status=status,
            default_calendar_id=default_calendar_id,
            default_language=default_language,
            is_active=is_active,
            opened_at=opened_at,
            closed_at=closed_at,
            created_at=created_at or now,
            updated_at=updated_at or now,
            notes=notes,
            version=1,
        )

    @property
    def display_name(self) -> str:
        return self.name

    @display_name.setter
    def display_name(self, value: str) -> None:
        self.name = value


@dataclass
class Department:
    id: str
    organization_id: str
    department_code: str
    name: str
    description: str = ""
    site_id: str | None = None
    parent_department_id: str | None = None
    department_type: str = ""
    cost_center_code: str = ""
    manager_employee_id: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        organization_id: str,
        department_code: str,
        name: str,
        *,
        description: str = "",
        site_id: str | None = None,
        parent_department_id: str | None = None,
        department_type: str = "",
        cost_center_code: str = "",
        manager_employee_id: str | None = None,
        is_active: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        notes: str = "",
    ) -> "Department":
        now = datetime.now(dt_timezone.utc)
        return Department(
            id=generate_id(),
            organization_id=organization_id,
            department_code=department_code,
            name=name,
            description=description,
            site_id=site_id,
            parent_department_id=parent_department_id,
            department_type=department_type,
            cost_center_code=cost_center_code,
            manager_employee_id=manager_employee_id,
            is_active=is_active,
            created_at=created_at or now,
            updated_at=updated_at or now,
            notes=notes,
            version=1,
        )

    @property
    def display_name(self) -> str:
        return self.name

    @display_name.setter
    def display_name(self, value: str) -> None:
        self.name = value


@dataclass
class Employee:
    id: str
    employee_code: str
    full_name: str
    department_id: str | None = None
    department: str = ""
    site_id: str | None = None
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
        department_id: str | None = None,
        department: str = "",
        site_id: str | None = None,
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
            department_id=department_id,
            department=department,
            site_id=site_id,
            site_name=site_name,
            title=title,
            employment_type=employment_type,
            email=email,
            phone=phone,
            is_active=is_active,
            version=1,
        )

__all__ = ["Department", "Employee", "EmploymentType", "Organization", "Site"]
