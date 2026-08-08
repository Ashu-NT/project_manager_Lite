from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum

from pydantic import field_validator

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


class RegisterEntryType(str, Enum):
    RISK = "RISK"
    ISSUE = "ISSUE"
    CHANGE = "CHANGE"


class RegisterEntrySeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RegisterEntryStatus(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    MITIGATED = "MITIGATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


_REGISTER_SEVERITY_PRIORITY = {
    RegisterEntrySeverity.CRITICAL: 0,
    RegisterEntrySeverity.HIGH: 1,
    RegisterEntrySeverity.MEDIUM: 2,
    RegisterEntrySeverity.LOW: 3,
}
_TERMINAL_REGISTER_STATUSES = {
    RegisterEntryStatus.APPROVED,
    RegisterEntryStatus.REJECTED,
    RegisterEntryStatus.CLOSED,
}


def as_register_entry_type(value: RegisterEntryType | str) -> RegisterEntryType:
    if isinstance(value, RegisterEntryType):
        return value
    raw = normalize_optional_text(value).upper()
    try:
        return RegisterEntryType(raw)
    except ValueError as exc:
        raise ValidationError(
            "Register entry type is invalid.",
            code="REGISTER_ENTRY_TYPE_INVALID",
        ) from exc


def as_register_entry_severity(value: RegisterEntrySeverity | str) -> RegisterEntrySeverity:
    if isinstance(value, RegisterEntrySeverity):
        return value
    raw = normalize_optional_text(value).upper()
    try:
        return RegisterEntrySeverity(raw)
    except ValueError as exc:
        raise ValidationError(
            "Register entry severity is invalid.",
            code="REGISTER_ENTRY_SEVERITY_INVALID",
        ) from exc


def as_register_entry_status(value: RegisterEntryStatus | str) -> RegisterEntryStatus:
    if isinstance(value, RegisterEntryStatus):
        return value
    raw = normalize_optional_text(value).upper()
    try:
        return RegisterEntryStatus(raw)
    except ValueError as exc:
        raise ValidationError(
            "Register entry status is invalid.",
            code="REGISTER_ENTRY_STATUS_INVALID",
        ) from exc


@validated_dataclass
class RegisterEntry:
    id: str
    project_id: str
    entry_type: RegisterEntryType
    title: str
    code: str = ""
    description: str = ""
    severity: RegisterEntrySeverity = RegisterEntrySeverity.MEDIUM
    status: RegisterEntryStatus = RegisterEntryStatus.OPEN
    owner_name: str | None = None
    due_date: date | None = None
    impact_summary: str = ""
    response_plan: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    def is_overdue_on(self, as_of: date) -> bool:
        return (
            self.due_date is not None
            and self.status not in _TERMINAL_REGISTER_STATUSES
            and self.due_date < as_of
        )

    def triage_key(self, as_of: date) -> tuple[int, int, date, str]:
        return (
            _REGISTER_SEVERITY_PRIORITY[self.severity],
            0 if self.is_overdue_on(as_of) else 1,
            self.due_date or date.max,
            self.title.casefold(),
        )

    @field_validator("project_id", mode="before")
    @classmethod
    def _validate_project_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Project ID is required.",
            code="REGISTER_PROJECT_REQUIRED",
        )

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Register title cannot be empty.",
            code="REGISTER_TITLE_EMPTY",
        )

    @field_validator("entry_type", mode="before")
    @classmethod
    def _validate_entry_type(cls, value: object) -> RegisterEntryType:
        return as_register_entry_type(value)

    @field_validator("severity", mode="before")
    @classmethod
    def _validate_severity(cls, value: object) -> RegisterEntrySeverity:
        return as_register_entry_severity(value)

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> RegisterEntryStatus:
        return as_register_entry_status(value)

    @field_validator("code", "description", "impact_summary", "response_plan", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("owner_name", mode="before")
    @classmethod
    def _normalize_owner_name(cls, value: object) -> str | None:
        normalized = normalize_optional_text(value)
        return normalized or None

    @field_validator("due_date", mode="before")
    @classmethod
    def _validate_due_date(cls, value: object) -> date | None:
        if value in (None, ""):
            return None
        if not isinstance(value, date):
            raise ValidationError(
                "Register due date must be a valid date.",
                code="REGISTER_DUE_DATE_INVALID",
            )
        return value

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object) -> datetime | None:
        if value in (None, ""):
            return None
        if not isinstance(value, datetime):
            raise ValidationError(
                "Register timestamps must be valid datetimes.",
                code="REGISTER_TIMESTAMP_INVALID",
            )
        return value

    @staticmethod
    def create(
        project_id: str,
        *,
        entry_type: RegisterEntryType,
        title: str,
        code: str = "",
        description: str = "",
        severity: RegisterEntrySeverity = RegisterEntrySeverity.MEDIUM,
        status: RegisterEntryStatus = RegisterEntryStatus.OPEN,
        owner_name: str | None = None,
        due_date: date | None = None,
        impact_summary: str = "",
        response_plan: str = "",
    ) -> "RegisterEntry":
        now = datetime.now(timezone.utc)
        return RegisterEntry(
            id=generate_id(),
            project_id=project_id,
            entry_type=entry_type,
            title=title,
            code=code,
            description=description,
            severity=severity,
            status=status,
            owner_name=owner_name,
            due_date=due_date,
            impact_summary=impact_summary,
            response_plan=response_plan,
            created_at=now,
            updated_at=now,
        )


__all__ = [
    "RegisterEntry",
    "RegisterEntryType",
    "RegisterEntrySeverity",
    "RegisterEntryStatus",
    "as_register_entry_type",
    "as_register_entry_severity",
    "as_register_entry_status",
]
