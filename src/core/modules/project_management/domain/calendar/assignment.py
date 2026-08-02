"""PM module calendar assignment domain models."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import field_validator, model_validator

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import normalize_required_text, validated_dataclass


def _normalize_optional_date(value: object) -> date | None:
    if value in (None, ""):
        return None
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ValidationError(
            "Calendar assignment dates must be valid dates.",
            code="PM_CALENDAR_ASSIGNMENT_DATE_INVALID",
        )
    return value


def _normalize_int(value: object, *, default: int = 0) -> int:
    try:
        return int(value if value not in (None, "") else default)
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            "Calendar assignment priority must be an integer.",
            code="PM_CALENDAR_ASSIGNMENT_PRIORITY_INVALID",
        ) from exc


@validated_dataclass
class ProjectCalendarAssignment:
    id: str
    project_id: str
    calendar_id: str
    effective_from: date | None = None
    effective_to: date | None = None
    is_default: bool = False
    priority: int = 0

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Project calendar assignment ID is required.",
            code="PROJECT_CALENDAR_ASSIGNMENT_ID_REQUIRED",
        )

    @field_validator("project_id", mode="before")
    @classmethod
    def _validate_project_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Project ID is required.",
            code="PROJECT_CALENDAR_ASSIGNMENT_PROJECT_REQUIRED",
        )

    @field_validator("calendar_id", mode="before")
    @classmethod
    def _validate_calendar_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Calendar ID is required.",
            code="PROJECT_CALENDAR_ASSIGNMENT_CALENDAR_REQUIRED",
        )

    @field_validator("effective_from", "effective_to", mode="before")
    @classmethod
    def _validate_dates(cls, value: object) -> date | None:
        return _normalize_optional_date(value)

    @field_validator("priority", mode="before")
    @classmethod
    def _normalize_priority(cls, value: object) -> int:
        return _normalize_int(value, default=0)

    @model_validator(mode="after")
    def _validate_effective_range(self) -> "ProjectCalendarAssignment":
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValidationError(
                "effective_to must be after effective_from.",
                code="PROJECT_CALENDAR_ASSIGNMENT_DATE_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        project_id: str,
        calendar_id: str,
        *,
        effective_from: date | None = None,
        effective_to: date | None = None,
        is_default: bool = False,
        priority: int = 0,
    ) -> "ProjectCalendarAssignment":
        return ProjectCalendarAssignment(
            id=generate_id(),
            project_id=project_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )


@validated_dataclass
class ResourceCalendarAssignment:
    id: str
    resource_id: str
    calendar_id: str
    effective_from: date | None = None
    effective_to: date | None = None
    is_default: bool = False
    priority: int = 0

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Resource calendar assignment ID is required.",
            code="RESOURCE_CALENDAR_ASSIGNMENT_ID_REQUIRED",
        )

    @field_validator("resource_id", mode="before")
    @classmethod
    def _validate_resource_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Resource ID is required.",
            code="RESOURCE_CALENDAR_ASSIGNMENT_RESOURCE_REQUIRED",
        )

    @field_validator("calendar_id", mode="before")
    @classmethod
    def _validate_calendar_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Calendar ID is required.",
            code="RESOURCE_CALENDAR_ASSIGNMENT_CALENDAR_REQUIRED",
        )

    @field_validator("effective_from", "effective_to", mode="before")
    @classmethod
    def _validate_dates(cls, value: object) -> date | None:
        return _normalize_optional_date(value)

    @field_validator("priority", mode="before")
    @classmethod
    def _normalize_priority(cls, value: object) -> int:
        return _normalize_int(value, default=0)

    @model_validator(mode="after")
    def _validate_effective_range(self) -> "ResourceCalendarAssignment":
        if (
            self.effective_from is not None
            and self.effective_to is not None
            and self.effective_to < self.effective_from
        ):
            raise ValidationError(
                "effective_to must be after effective_from.",
                code="RESOURCE_CALENDAR_ASSIGNMENT_DATE_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        resource_id: str,
        calendar_id: str,
        *,
        effective_from: date | None = None,
        effective_to: date | None = None,
        is_default: bool = False,
        priority: int = 0,
    ) -> "ResourceCalendarAssignment":
        return ResourceCalendarAssignment(
            id=generate_id(),
            resource_id=resource_id,
            calendar_id=calendar_id,
            effective_from=effective_from,
            effective_to=effective_to,
            is_default=is_default,
            priority=priority,
        )


__all__ = ["ProjectCalendarAssignment", "ResourceCalendarAssignment"]
