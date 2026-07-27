from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone

from pydantic import field_validator, model_validator

from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


def _coerce_presence_datetime(value: object, *, code: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError("Task presence timestamps must be valid datetimes.", code=code)
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@validated_dataclass
class TaskPresence:
    id: str
    task_id: str
    user_id: str | None
    username: str
    display_name: str | None = None
    activity: str = "reviewing"
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Task presence ID is required.",
            code="TASK_PRESENCE_ID_REQUIRED",
        )

    @field_validator("task_id", mode="before")
    @classmethod
    def _validate_task_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Task ID is required.",
            code="TASK_PRESENCE_TASK_REQUIRED",
        )

    @field_validator("user_id", mode="before")
    @classmethod
    def _normalize_user_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("username", mode="before")
    @classmethod
    def _validate_username(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Presence username is required.",
            code="TASK_PRESENCE_USERNAME_REQUIRED",
        ).lower()

    @field_validator("display_name", mode="before")
    @classmethod
    def _normalize_display_name(cls, value: object) -> str | None:
        normalized = normalize_optional_text(value)
        return normalized or None

    @field_validator("activity", mode="before")
    @classmethod
    def _normalize_activity(cls, value: object) -> str:
        return normalize_optional_text(value).lower() or "reviewing"

    @field_validator("started_at", "last_seen_at", mode="before")
    @classmethod
    def _validate_timestamps(cls, value: object) -> datetime:
        return _coerce_presence_datetime(value, code="TASK_PRESENCE_TIMESTAMP_INVALID")

    @model_validator(mode="after")
    def _validate_seen_window(self) -> "TaskPresence":
        if self.last_seen_at < self.started_at:
            raise ValidationError(
                "Presence last-seen time cannot be before the started time.",
                code="TASK_PRESENCE_SEEN_RANGE_INVALID",
            )
        return self

    @staticmethod
    def create(*, task_id: str, user_id: str | None, username: str, display_name: str | None = None, activity: str = "reviewing") -> "TaskPresence":
        now = datetime.now(timezone.utc)
        return TaskPresence(
            id=generate_id(), task_id=task_id, user_id=user_id,
            username=username,
            display_name=display_name,
            activity=activity,
            started_at=now, last_seen_at=now,
        )


@dataclass(frozen=True)
class TaskPresenceStatusItem:
    task_id: str
    task_name: str
    project_id: str
    project_name: str
    username: str
    display_name: str | None = None
    activity: str = "reviewing"
    last_seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_self: bool = False


__all__ = ["TaskPresence", "TaskPresenceStatusItem"]
