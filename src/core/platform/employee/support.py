from __future__ import annotations

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.employee.domain import Employee, EmploymentType


def normalize_email(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    return normalized or None


def normalize_phone(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def coerce_employment_type(value: EmploymentType | str | None) -> EmploymentType:
    if isinstance(value, EmploymentType):
        return value
    raw = str(value or EmploymentType.FULL_TIME.value).strip().upper()
    try:
        return EmploymentType(raw)
    except ValueError as exc:
        raise ValidationError("Employment type is invalid.", code="EMPLOYEE_TYPE_INVALID") from exc


def employee_contact(employee: Employee) -> str:
    return employee.email or employee.phone or ""


__all__ = [
    "coerce_employment_type",
    "employee_contact",
    "normalize_email",
    "normalize_phone",
]
