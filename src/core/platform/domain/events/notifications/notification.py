from __future__ import annotations

from dataclasses import field
from datetime import datetime, timezone
from typing import Any

from pydantic import field_validator

from src.core.platform.auth.datetime_utils import ensure_utc_datetime
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_required_text,
    validated_dataclass,
)


def _normalize_notification_datetime(
    value: object,
    *,
    code: str,
    required: bool = False,
) -> datetime | None:
    if value in (None, ""):
        if required:
            raise ValidationError(
                "Notification timestamp is required.",
                code=code,
            )
        return None
    if not isinstance(value, datetime):
        raise ValidationError(
            "Notification timestamps must be valid datetimes.",
            code=code,
        )
    return ensure_utc_datetime(value)


@validated_dataclass
class Notification:
    """A single in-app notification addressed to one user."""

    id: str
    recipient_user_id: str
    tenant_id: str | None
    category: str
    title: str
    body: str
    created_at: datetime
    read_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @field_validator("id", "recipient_user_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Notification id and recipient are required.",
            code="NOTIFICATION_REFERENCE_REQUIRED",
        )

    @field_validator("tenant_id", mode="before")
    @classmethod
    def _normalize_tenant_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("category", "title", "body", mode="before")
    @classmethod
    def _validate_required_text(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Notification category, title, and body are required.",
            code="NOTIFICATION_CONTENT_REQUIRED",
        )

    @field_validator("created_at", mode="before")
    @classmethod
    def _validate_created_at(cls, value: object) -> datetime:
        return _normalize_notification_datetime(
            value,
            code="NOTIFICATION_CREATED_AT_REQUIRED",
            required=True,
        )

    @field_validator("read_at", mode="before")
    @classmethod
    def _validate_read_at(cls, value: object) -> datetime | None:
        return _normalize_notification_datetime(
            value,
            code="NOTIFICATION_READ_AT_INVALID",
        )

    @staticmethod
    def create(
        *,
        recipient_user_id: str,
        category: str,
        title: str,
        body: str,
        tenant_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Notification":
        return Notification(
            id=generate_id(),
            recipient_user_id=recipient_user_id,
            tenant_id=tenant_id,
            category=category,
            title=title,
            body=body,
            created_at=datetime.now(timezone.utc),
            read_at=None,
            metadata=metadata or {},
        )

    @property
    def is_read(self) -> bool:
        return self.read_at is not None


__all__ = ["Notification"]
