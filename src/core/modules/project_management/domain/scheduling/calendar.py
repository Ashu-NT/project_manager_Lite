from __future__ import annotations

from datetime import date

from pydantic import field_validator, model_validator

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.common.exceptions import ValidationError


@validated_dataclass
class CalendarEvent:
    """A project calendar event optionally linked to project or task."""

    id: str
    title: str
    start_date: date
    end_date: date
    project_id: str | None = None
    task_id: str | None = None
    all_day: bool = True
    description: str = ""

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Calendar event title cannot be empty.",
            code="EVENT_TITLE_EMPTY",
        )

    @field_validator("project_id", mode="before")
    @classmethod
    def _validate_project_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Calendar event project is required.",
            code="EVENT_PROJECT_REQUIRED",
        )

    @field_validator("task_id", mode="before")
    @classmethod
    def _normalize_task_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("description", mode="before")
    @classmethod
    def _normalize_description(cls, value: object) -> str:
        return normalize_optional_text(value)

    @model_validator(mode="after")
    def _validate_date_range(self) -> "CalendarEvent":
        if self.end_date < self.start_date:
            raise ValidationError(
                "Event end date cannot be before start date.",
                code="EVENT_DATE_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        title: str,
        start_date: date,
        end_date: date,
        project_id: str | None = None,
        task_id: str | None = None,
        all_day: bool = True,
        description: str = "",
    ) -> "CalendarEvent":
        return CalendarEvent(
            id=generate_id(),
            title=title,
            start_date=start_date,
            end_date=end_date,
            project_id=project_id,
            task_id=task_id,
            all_day=all_day,
            description=description,
        )

__all__ = ["CalendarEvent"]
