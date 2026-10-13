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


class EmployeeLifecycleStatus(str, Enum):
    """The sole lifecycle source of truth -- never a second `is_active`
    boolean alongside it. Only ACTIVE/INACTIVE exist today; richer states
    (ON_LEAVE, TERMINATED, ...) belong to a future Employment Relationship
    model once real hire/termination/leave requirements exist, not this
    master-record lifecycle."""

    ACTIVE = "active"
    INACTIVE = "inactive"


def coerce_employee_lifecycle_status(
    value: EmployeeLifecycleStatus | str | None,
) -> EmployeeLifecycleStatus:
    if isinstance(value, EmployeeLifecycleStatus):
        return value
    raw = normalize_optional_text(value).lower() or EmployeeLifecycleStatus.ACTIVE.value
    try:
        return EmployeeLifecycleStatus(raw)
    except ValueError as exc:
        raise ValidationError(
            "Employee lifecycle status is invalid.", code="EMPLOYEE_STATUS_INVALID"
        ) from exc


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
    status: EmployeeLifecycleStatus = EmployeeLifecycleStatus.ACTIVE
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

    @field_validator("site_id", "user_id", mode="before")
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("organization_id", mode="before")
    @classmethod
    def _validate_organization_id(cls, value: object) -> str:
        # Required, not optional: every real construction path already
        # resolves the active organization before building an Employee (the
        # annotation stays `str | None` only to avoid reordering this
        # dataclass's fields; every call site uses keyword args). Making
        # this precise closes the gap where the domain layer permitted a
        # None the application layer never actually produced.
        return normalize_required_text(
            value,
            message="Employee must belong to an organization.",
            code="EMPLOYEE_ORGANIZATION_REQUIRED",
        )

    @field_validator("department_id", mode="before")
    @classmethod
    def _validate_department_id(cls, value: object) -> str:
        # Every Employee belongs to exactly one Department -- required, not
        # optional, unlike site_id/user_id above. The annotation stays
        # `str | None` only to avoid reordering this dataclass's fields
        # (every real construction site passes keyword args); this
        # validator is what actually makes it required at runtime.
        return normalize_required_text(
            value,
            message="Employee must be assigned to a department.",
            code="EMPLOYEE_DEPARTMENT_REQUIRED",
        )

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

    @field_validator("status", mode="before")
    @classmethod
    def _coerce_status(cls, value: EmployeeLifecycleStatus | str | None) -> EmployeeLifecycleStatus:
        return coerce_employee_lifecycle_status(value)

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

    @property
    def is_active(self) -> bool:
        """Computed from status -- never a second persisted source of truth."""
        return self.status == EmployeeLifecycleStatus.ACTIVE

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
        user_id: str | None = None,
    ) -> Employee:
        # No `status`/`is_active` parameter -- every new Employee starts
        # ACTIVE (EmployeeLifecycleStatus's own default). Use
        # activate_employee/deactivate_employee to change it afterward.
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
            user_id=user_id,
            version=1,
        )


__all__ = [
    "Employee",
    "EmployeeLifecycleStatus",
    "EmploymentType",
    "coerce_employee_lifecycle_status",
    "coerce_employment_type",
    "normalize_email",
    "normalize_phone",
]
