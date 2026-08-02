from __future__ import annotations

from src.core.platform.employee.domain import Employee, coerce_employment_type, normalize_email, normalize_phone


def employee_contact(employee: Employee) -> str:
    return employee.email or employee.phone or ""


__all__ = [
    "coerce_employment_type",
    "employee_contact",
    "normalize_email",
    "normalize_phone",
]
