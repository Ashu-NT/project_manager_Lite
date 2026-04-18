from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from core.platform.common.ids import generate_id


class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    TEMPORARY = "TEMPORARY"


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


__all__ = ["Employee", "EmploymentType"]
