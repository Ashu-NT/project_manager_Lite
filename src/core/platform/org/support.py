from __future__ import annotations

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.org.domain import Employee, EmploymentType


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


DEFAULT_ORGANIZATION_CODE = "DEFAULT"
DEFAULT_ORGANIZATION_NAME = "Default Organization"
DEFAULT_ORGANIZATION_TIMEZONE = "UTC"
DEFAULT_ORGANIZATION_CURRENCY = "EUR"


def normalize_code(value: str, *, label: str) -> str:
    normalized = (value or "").strip().upper()
    if not normalized:
        raise ValidationError(f"{label} is required.", code=f"{label.upper().replace(' ', '_')}_REQUIRED")
    return normalized


def normalize_name(value: str, *, label: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ValidationError(f"{label} is required.", code=f"{label.upper().replace(' ', '_')}_REQUIRED")
    return normalized


__all__ = [
    "DEFAULT_ORGANIZATION_CODE",
    "DEFAULT_ORGANIZATION_CURRENCY",
    "DEFAULT_ORGANIZATION_NAME",
    "DEFAULT_ORGANIZATION_TIMEZONE",
    "coerce_employment_type",
    "employee_contact",
    "normalize_code",
    "normalize_email",
    "normalize_name",
    "normalize_phone",
]
