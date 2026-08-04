from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

from pydantic import field_validator

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


@validated_dataclass
class Department:
    id: str
    organization_id: str
    department_code: str
    name: str
    description: str = ""
    site_id: str | None = None
    default_location_id: str | None = None
    parent_department_id: str | None = None
    department_type: str = ""
    cost_center_code: str = ""
    manager_employee_id: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @field_validator("organization_id", mode="before")
    @classmethod
    def _validate_organization_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Organization ID is required.",
            code="DEPARTMENT_ORGANIZATION_REQUIRED",
        )

    @field_validator("department_code", mode="before")
    @classmethod
    def _validate_department_code(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Department code is required.",
            code="DEPARTMENT_CODE_REQUIRED",
        ).upper()

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Department name is required.",
            code="DEPARTMENT_NAME_REQUIRED",
        )

    @field_validator(
        "site_id",
        "default_location_id",
        "parent_department_id",
        "manager_employee_id",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("description", "department_type", "notes", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("cost_center_code", mode="before")
    @classmethod
    def _normalize_cost_center_code(cls, value: object) -> str:
        return normalize_optional_text(value).upper()

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_datetimes(cls, value: object) -> datetime | None:
        if value in (None, ""):
            return None
        if not isinstance(value, datetime):
            raise ValidationError(
                "Department timestamps must be valid datetimes.",
                code="DEPARTMENT_TIMESTAMP_INVALID",
            )
        return value

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        resolved = int(value if value not in (None, "") else 1)
        if resolved < 1:
            raise ValidationError(
                "Department version must be positive.",
                code="DEPARTMENT_VERSION_INVALID",
            )
        return resolved

    @staticmethod
    def create(
        organization_id: str,
        department_code: str,
        name: str,
        *,
        description: str = "",
        site_id: str | None = None,
        default_location_id: str | None = None,
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
            default_location_id=default_location_id,
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


__all__ = ["Department"]
