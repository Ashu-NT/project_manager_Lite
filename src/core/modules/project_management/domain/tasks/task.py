from __future__ import annotations

from datetime import date, datetime
import re

from pydantic import field_validator, model_validator

from src.core.modules.project_management.domain.enums import DependencyType, TaskStatus
from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)

_INVALID_TASK_NAME_CHARACTERS = {"/", "\\", "?", "%", "*", ":", "|", '"', "<", ">"}
_WBS_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


@validated_dataclass
class Task:
    id: str
    project_id: str
    name: str
    code: str = ""
    parent_task_id: str | None = None
    wbs_code: str = ""
    sort_order: int = 0
    description: str = ""
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: int = 0
    percent_complete: float = 0.0
    actual_start: date | None = None
    actual_end: date | None = None
    deadline: date | None = None
    constraint_type: str | None = None
    constraint_date: date | None = None
    version: int = 1

    @field_validator("project_id", mode="before")
    @classmethod
    def _validate_project_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Project ID is required.",
            code="TASK_PROJECT_REQUIRED",
        )

    @field_validator("parent_task_id", mode="before")
    @classmethod
    def _normalize_parent_task_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("wbs_code", mode="before")
    @classmethod
    def _validate_wbs_code(cls, value: object) -> str:
        normalized = normalize_optional_text(value).upper()
        if normalized and not _WBS_CODE_PATTERN.fullmatch(normalized):
            raise ValidationError(
                "WBS code must be 1-64 letters, numbers, dots, hyphens, or underscores.",
                code="TASK_WBS_CODE_INVALID",
            )
        return normalized

    @field_validator("sort_order", mode="before")
    @classmethod
    def _validate_sort_order(cls, value: object) -> int:
        resolved = int(value if value not in (None, "") else 0)
        if resolved < 0:
            raise ValidationError(
                "Task sort_order cannot be negative.",
                code="TASK_SORT_ORDER_INVALID",
            )
        return resolved

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, value: object) -> str:
        normalized = normalize_required_text(
            value,
            message="Task name cannot be empty.",
            code="TASK_NAME_EMPTY",
        )
        if len(normalized) < 3:
            raise ValidationError(
                "Task name must be at least 3 characters.",
                code="TASK_NAME_TOO_SHORT",
            )
        if any(char in normalized for char in _INVALID_TASK_NAME_CHARACTERS):
            raise ValidationError(
                "Task name contains invalid characters.",
                code="TASK_NAME_INVALID_CHARS",
            )
        return normalized

    @field_validator("code", "description", "constraint_type", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("duration_days", mode="before")
    @classmethod
    def _validate_duration_days(cls, value: object) -> int | None:
        if value in (None, ""):
            return None
        resolved = int(value)
        if resolved < 0:
            raise ValidationError(
                "Task duration_days cannot be negative.",
                code="TASK_DURATION_INVALID",
            )
        return resolved

    @field_validator("percent_complete", mode="before")
    @classmethod
    def _validate_percent_complete(cls, value: object) -> float:
        resolved = float(value if value not in (None, "") else 0.0)
        if resolved < 0 or resolved > 100:
            raise ValidationError(
                "percent_complete must be between 0 and 100.",
                code="TASK_PERCENT_COMPLETE_INVALID",
            )
        return resolved

    @model_validator(mode="after")
    def _validate_date_ranges(self) -> "Task":
        if not self.wbs_code:
            self.wbs_code = str(self.id or "").strip().upper()
        if not self.wbs_code or not _WBS_CODE_PATTERN.fullmatch(self.wbs_code):
            raise ValidationError(
                "Task requires a valid WBS code.",
                code="TASK_WBS_CODE_INVALID",
            )
        if self.parent_task_id == self.id:
            raise ValidationError(
                "A task cannot be its own parent.",
                code="TASK_WBS_SELF_PARENT",
            )
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                "Task end date cannot be before start date.",
                code="TASK_DATE_RANGE_INVALID",
            )
        if self.start_date and self.deadline and self.deadline < self.start_date:
            raise ValidationError(
                (
                    f"Task deadline {self.deadline!s} cannot be before "
                    f"start_date {self.start_date!s}. Task id: {self.id}"
                ),
                code="TASK_DEADLINE_INVALID",
            )
        if self.actual_start and self.actual_end and self.actual_end < self.actual_start:
            raise ValidationError(
                "Actual end date cannot be before actual start.",
                code="TASK_ACTUAL_DATE_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(project_id: str, name: str, description: str = "", **extra) -> "Task":
        return Task(
            id=generate_id(),
            project_id=project_id,
            name=name,
            description=description,
            **extra,
        )


@validated_dataclass
class TaskAssignment:
    id: str
    task_id: str
    resource_id: str
    allocation_percent: float = 100.0
    hours_logged: float = 0.0
    project_resource_id: str | None = None
    response_status: str = "pending"
    responded_at: datetime | None = None

    @field_validator("task_id", mode="before")
    @classmethod
    def _validate_task_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Task ID is required.",
            code="ASSIGNMENT_TASK_REQUIRED",
        )

    @field_validator("resource_id", mode="before")
    @classmethod
    def _validate_resource_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Resource ID is required.",
            code="ASSIGNMENT_RESOURCE_REQUIRED",
        )

    @field_validator("project_resource_id", mode="before")
    @classmethod
    def _normalize_project_resource_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("allocation_percent", mode="before")
    @classmethod
    def _validate_allocation_percent(cls, value: object) -> float:
        resolved = float(value if value not in (None, "") else 0.0)
        if resolved <= 0 or resolved > 100:
            raise ValidationError(
                "allocation_percent must be > 0 and <= 100.",
                code="ASSIGNMENT_ALLOCATION_INVALID",
            )
        return resolved

    @field_validator("hours_logged", mode="before")
    @classmethod
    def _validate_hours_logged(cls, value: object) -> float:
        resolved = float(value if value not in (None, "") else 0.0)
        if resolved < 0:
            raise ValidationError(
                "hours_logged cannot be negative.",
                code="ASSIGNMENT_HOURS_INVALID",
            )
        return resolved

    @field_validator("response_status", mode="before")
    @classmethod
    def _validate_response_status(cls, value: object) -> str:
        normalized = normalize_optional_text(value).lower() or "pending"
        if normalized not in {"pending", "accepted", "declined"}:
            raise ValidationError(
                "response_status must be one of: pending, accepted, declined.",
                code="ASSIGNMENT_RESPONSE_STATUS_INVALID",
            )
        return normalized

    @field_validator("responded_at", mode="before")
    @classmethod
    def _validate_responded_at(cls, value: object) -> datetime | None:
        if value is None:
            return None
        if not isinstance(value, datetime):
            raise ValidationError(
                "responded_at must be a valid datetime.",
                code="ASSIGNMENT_RESPONDED_AT_INVALID",
            )
        return value

    @property
    def is_response_pending(self) -> bool:
        return self.response_status == "pending"

    @staticmethod
    def create(
        task_id: str,
        resource_id: str,
        allocation_percent: float = 100.0,
        hours_logged: float = 0.0,
    ) -> "TaskAssignment":
        return TaskAssignment(
            id=generate_id(),
            task_id=task_id,
            resource_id=resource_id,
            allocation_percent=allocation_percent,
            hours_logged=hours_logged,
        )


@validated_dataclass
class TaskDependency:
    id: str
    predecessor_task_id: str
    successor_task_id: str
    dependency_type: DependencyType = DependencyType.FINISH_TO_START
    lag_days: int = 0

    @field_validator("predecessor_task_id", mode="before")
    @classmethod
    def _validate_predecessor_task_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Predecessor task ID is required.",
            code="DEPENDENCY_PREDECESSOR_REQUIRED",
        )

    @field_validator("successor_task_id", mode="before")
    @classmethod
    def _validate_successor_task_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Successor task ID is required.",
            code="DEPENDENCY_SUCCESSOR_REQUIRED",
        )

    @field_validator("lag_days", mode="before")
    @classmethod
    def _validate_lag_days(cls, value: object) -> int:
        return int(value if value not in (None, "") else 0)

    @model_validator(mode="after")
    def _validate_not_self_dependency(self) -> "TaskDependency":
        if self.predecessor_task_id == self.successor_task_id:
            raise ValidationError(
                "A task cannot depend on itself.",
                code="DEPENDENCY_SELF",
            )
        return self

    @staticmethod
    def create(
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        lag_days: int = 0,
    ) -> "TaskDependency":
        return TaskDependency(
            id=generate_id(),
            predecessor_task_id=predecessor_id,
            successor_task_id=successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
        )


__all__ = ["Task", "TaskAssignment", "TaskDependency"]
