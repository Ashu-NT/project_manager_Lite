from __future__ import annotations

from enum import Enum

from pydantic import field_validator

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    TEMPORARY = "TEMPORARY"


def coerce_employment_type(value: EmploymentType | str | None) -> EmploymentType:
    if isinstance(value, EmploymentType):
        return value
    raw = normalize_optional_text(value).upper() or EmploymentType.FULL_TIME.value
    try:
        return EmploymentType(raw)
    except ValueError as exc:
        raise ValidationError("Employment type is invalid.", code="EMPLOYEE_TYPE_INVALID") from exc


def normalize_email(value: object) -> str | None:
    normalized = normalize_optional_text(value).lower()
    return normalized or None


def normalize_phone(value: object) -> str | None:
    normalized = normalize_optional_text(value)
    return normalized or None


@validated_dataclass
class Employee:
    id: str
    employee_code: str
    full_name: str
    organization_id: str | None = None
    department_id: str | None = None
    department: str = ""
    site_id: str | None = None
    site_name: str = ""
    title: str = ""
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    email: str | None = None
    phone: str | None = None
    is_active: bool = True
    user_id: str | None = None
    version: int = 1

    @field_validator("employee_code", mode="before")
    @classmethod
    def _validate_employee_code(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Employee code is required.",
            code="EMPLOYEE_CODE_REQUIRED",
        ).upper()

    @field_validator("full_name", mode="before")
    @classmethod
    def _validate_full_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Employee name is required.",
            code="EMPLOYEE_NAME_REQUIRED",
        )

    @field_validator("organization_id", "department_id", "site_id", "user_id", mode="before")
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("department", "site_name", "title", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("employment_type", mode="before")
    @classmethod
    def _coerce_employment_type(cls, value: EmploymentType | str | None) -> EmploymentType:
        return coerce_employment_type(value)

    @field_validator("email", mode="before")
    @classmethod
    def _normalize_email(cls, value: object) -> str | None:
        return normalize_email(value)

    @field_validator("phone", mode="before")
    @classmethod
    def _normalize_phone(cls, value: object) -> str | None:
        return normalize_phone(value)

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        resolved = int(value if value not in (None, "") else 1)
        if resolved < 1:
            raise ValidationError(
                "Employee version must be positive.",
                code="EMPLOYEE_VERSION_INVALID",
            )
        return resolved

    @staticmethod
    def create(
        employee_code: str,
        full_name: str,
        organization_id: str | None = None,
        department_id: str | None = None,
        department: str = "",
        site_id: str | None = None,
        site_name: str = "",
        title: str = "",
        employment_type: EmploymentType | str = EmploymentType.FULL_TIME,
        email: str | None = None,
        phone: str | None = None,
        is_active: bool = True,
        user_id: str | None = None,
    ) -> "Employee":
        return Employee(
            id=generate_id(),
            employee_code=employee_code,
            full_name=full_name,
            organization_id=organization_id,
            department_id=department_id,
            department=department,
            site_id=site_id,
            site_name=site_name,
            title=title,
            employment_type=employment_type,
            email=email,
            phone=phone,
            is_active=is_active,
            user_id=user_id,
            version=1,
        )


__all__ = [
    "Employee",
    "EmploymentType",
    "coerce_employment_type",
    "normalize_email",
    "normalize_phone",
]
