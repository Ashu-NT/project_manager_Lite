from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from pydantic import field_validator, model_validator

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


class TimesheetPeriodStatus(str, Enum):
    OPEN = "OPEN"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    LOCKED = "LOCKED"


def _validate_date(value: object, *, message: str, code: str) -> date:
    if not isinstance(value, date):
        raise ValidationError(message, code=code)
    return value


def _validate_optional_datetime(value: object, *, code: str) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, datetime):
        raise ValidationError("Timesheet timestamps must be valid datetimes.", code=code)
    return value


def normalize_time_entry_hours(value: object) -> float:
    try:
        resolved = float(value if value not in (None, "") else 0.0)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Time entry hours must be greater than zero.", code="TIME_ENTRY_HOURS_INVALID") from exc
    if resolved <= 0:
        raise ValidationError("Time entry hours must be greater than zero.", code="TIME_ENTRY_HOURS_INVALID")
    return resolved


def coerce_timesheet_period_status(value: TimesheetPeriodStatus | str | None) -> TimesheetPeriodStatus:
    if isinstance(value, TimesheetPeriodStatus):
        return value
    raw = normalize_optional_text(value).upper() or TimesheetPeriodStatus.OPEN.value
    try:
        return TimesheetPeriodStatus(raw)
    except ValueError as exc:
        raise ValidationError("Timesheet period status is invalid.", code="TIMESHEET_PERIOD_STATUS_INVALID") from exc


@validated_dataclass
class TimeEntry:
    id: str
    work_allocation_id: str
    entry_date: date
    hours: float
    organization_id: str | None = None
    assignment_id: str | None = None
    note: str = ""
    author_user_id: str | None = None
    author_username: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    owner_type: str = "work_allocation"
    owner_id: str | None = None
    owner_label: str = ""
    scope_type: str | None = None
    scope_id: str | None = None
    employee_id: str | None = None
    department_id: str | None = None
    department_name: str = ""
    site_id: str | None = None
    site_name: str = ""
    version: int = 1

    @field_validator("work_allocation_id", mode="before")
    @classmethod
    def _validate_work_allocation_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Work allocation ID is required.",
            code="TIME_ENTRY_WORK_ALLOCATION_REQUIRED",
        )

    @field_validator("entry_date", mode="before")
    @classmethod
    def _validate_entry_date(cls, value: object) -> date:
        return _validate_date(
            value,
            message="Time entry date is required.",
            code="TIME_ENTRY_DATE_INVALID",
        )

    @field_validator("hours", mode="before")
    @classmethod
    def _validate_hours(cls, value: object) -> float:
        return normalize_time_entry_hours(value)

    @field_validator(
        "organization_id",
        "assignment_id",
        "author_user_id",
        "owner_id",
        "scope_id",
        "employee_id",
        "department_id",
        "site_id",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("scope_type", mode="before")
    @classmethod
    def _normalize_scope_type(cls, value: object) -> str | None:
        normalized = normalize_optional_text(value)
        return normalized or None

    @field_validator("note", "author_username", "owner_label", "department_name", "site_name", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("owner_type", mode="before")
    @classmethod
    def _normalize_owner_type(cls, value: object) -> str:
        return normalize_optional_text(value) or "work_allocation"

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_datetimes(cls, value: object) -> datetime | None:
        return _validate_optional_datetime(value, code="TIME_ENTRY_TIMESTAMP_INVALID")

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        try:
            version = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Time entry version must be a positive integer.",
                code="TIME_ENTRY_VERSION_INVALID",
            ) from exc
        if version < 1:
            raise ValidationError(
                "Time entry version must be a positive integer.",
                code="TIME_ENTRY_VERSION_INVALID",
            )
        return version

    @model_validator(mode="after")
    def _validate_owner_state(self) -> "TimeEntry":
        assignment_id = self.assignment_id
        if assignment_id is None and self.owner_type == "task_assignment":
            assignment_id = self.work_allocation_id
            object.__setattr__(self, "assignment_id", assignment_id)
        if self.owner_id is None:
            object.__setattr__(self, "owner_id", assignment_id or self.work_allocation_id)
        return self

    @staticmethod
    def create(
        work_allocation_id: str,
        *,
        entry_date: date,
        hours: float,
        organization_id: str | None = None,
        assignment_id: str | None = None,
        note: str = "",
        author_user_id: str | None = None,
        author_username: str | None = None,
        owner_type: str = "work_allocation",
        owner_id: str | None = None,
        owner_label: str = "",
        scope_type: str | None = None,
        scope_id: str | None = None,
        employee_id: str | None = None,
        department_id: str | None = None,
        department_name: str = "",
        site_id: str | None = None,
        site_name: str = "",
    ) -> "TimeEntry":
        now = datetime.now(timezone.utc)
        return TimeEntry(
            id=generate_id(),
            work_allocation_id=work_allocation_id,
            entry_date=entry_date,
            hours=hours,
            organization_id=organization_id,
            assignment_id=assignment_id,
            note=note,
            author_user_id=author_user_id,
            author_username=author_username,
            created_at=now,
            updated_at=now,
            owner_type=owner_type,
            owner_id=owner_id,
            owner_label=owner_label,
            scope_type=scope_type,
            scope_id=scope_id,
            employee_id=employee_id,
            department_id=department_id,
            department_name=department_name,
            site_id=site_id,
            site_name=site_name,
        )


@validated_dataclass
class TimesheetPeriod:
    id: str
    resource_id: str
    period_start: date
    period_end: date
    organization_id: str | None = None
    status: TimesheetPeriodStatus = TimesheetPeriodStatus.OPEN
    submitted_at: datetime | None = None
    submitted_by_user_id: str | None = None
    submitted_by_username: str | None = None
    decided_at: datetime | None = None
    decided_by_user_id: str | None = None
    decided_by_username: str | None = None
    decision_note: str | None = None
    locked_at: datetime | None = None
    version: int = 1

    @field_validator("resource_id", mode="before")
    @classmethod
    def _validate_resource_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Timesheet resource ID is required.",
            code="TIMESHEET_PERIOD_RESOURCE_REQUIRED",
        )

    @field_validator("period_start", mode="before")
    @classmethod
    def _validate_period_start(cls, value: object) -> date:
        return _validate_date(
            value,
            message="Timesheet period start date is required.",
            code="TIMESHEET_PERIOD_START_INVALID",
        )

    @field_validator("period_end", mode="before")
    @classmethod
    def _validate_period_end(cls, value: object) -> date:
        return _validate_date(
            value,
            message="Timesheet period end date is required.",
            code="TIMESHEET_PERIOD_END_INVALID",
        )

    @field_validator("organization_id", "submitted_by_user_id", "decided_by_user_id", mode="before")
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("submitted_by_username", "decided_by_username", "decision_note", mode="before")
    @classmethod
    def _normalize_optional_text_fields(cls, value: object) -> str | None:
        normalized = normalize_optional_text(value)
        return normalized or None

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: TimesheetPeriodStatus | str | None) -> TimesheetPeriodStatus:
        return coerce_timesheet_period_status(value)

    @field_validator("submitted_at", "decided_at", "locked_at", mode="before")
    @classmethod
    def _validate_period_datetimes(cls, value: object) -> datetime | None:
        return _validate_optional_datetime(value, code="TIMESHEET_PERIOD_TIMESTAMP_INVALID")

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        try:
            version = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                "Timesheet period version must be a positive integer.",
                code="TIMESHEET_PERIOD_VERSION_INVALID",
            ) from exc
        if version < 1:
            raise ValidationError(
                "Timesheet period version must be a positive integer.",
                code="TIMESHEET_PERIOD_VERSION_INVALID",
            )
        return version

    @model_validator(mode="after")
    def _validate_period_range(self) -> "TimesheetPeriod":
        if self.period_end < self.period_start:
            raise ValidationError(
                "Timesheet period end date cannot be before period start date.",
                code="TIMESHEET_PERIOD_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(
        resource_id: str,
        *,
        period_start: date,
        period_end: date,
        organization_id: str | None = None,
    ) -> "TimesheetPeriod":
        return TimesheetPeriod(
            id=generate_id(),
            resource_id=resource_id,
            period_start=period_start,
            period_end=period_end,
            organization_id=organization_id,
        )


WorkEntry = TimeEntry


__all__ = [
    "TimeEntry",
    "TimesheetPeriod",
    "TimesheetPeriodStatus",
    "WorkEntry",
    "coerce_timesheet_period_status",
    "normalize_time_entry_hours",
]
