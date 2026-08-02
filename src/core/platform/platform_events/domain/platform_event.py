from __future__ import annotations

from collections.abc import Mapping
import uuid
from dataclasses import field
from datetime import datetime, timezone
from typing import Any

from pydantic import field_validator

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


def _normalize_required_datetime(value: object, *, code: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError(
            "Platform event timestamp must be a valid datetime.",
            code=code,
        )
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_metadata(value: object) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    raise ValidationError(
        "Platform event metadata must be a dictionary.",
        code="PLATFORM_EVENT_METADATA_INVALID",
    )


@validated_dataclass
class PlatformEvent:
    id: str
    operation: str
    actor_user_id: str | None
    tenant_id: str
    resource_type: str
    resource_id: str
    outcome: str
    severity: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    @field_validator("operation", mode="before")
    @classmethod
    def _validate_operation(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Platform event operation is required.",
            code="PLATFORM_EVENT_OPERATION_REQUIRED",
        ).lower()

    @field_validator("actor_user_id", mode="before")
    @classmethod
    def _normalize_actor_user_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("tenant_id", mode="before")
    @classmethod
    def _validate_tenant_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Platform event tenant ID is required.",
            code="PLATFORM_EVENT_TENANT_REQUIRED",
        )

    @field_validator("resource_type", mode="before")
    @classmethod
    def _validate_resource_type(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Platform event resource type is required.",
            code="PLATFORM_EVENT_RESOURCE_TYPE_REQUIRED",
        ).lower()

    @field_validator("resource_id", mode="before")
    @classmethod
    def _validate_resource_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Platform event resource ID is required.",
            code="PLATFORM_EVENT_RESOURCE_ID_REQUIRED",
        )

    @field_validator("outcome", mode="before")
    @classmethod
    def _normalize_outcome(cls, value: object) -> str:
        return normalize_optional_text(value).lower() or "success"

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, value: object) -> str:
        return normalize_optional_text(value).lower() or "low"

    @field_validator("created_at", mode="before")
    @classmethod
    def _validate_created_at(cls, value: object) -> datetime:
        return _normalize_required_datetime(
            value,
            code="PLATFORM_EVENT_CREATED_AT_INVALID",
        )

    @field_validator("metadata", mode="before")
    @classmethod
    def _validate_metadata(cls, value: object) -> dict[str, Any]:
        return _normalize_metadata(value)

    @classmethod
    def create(
        cls,
        *,
        operation: str,
        actor_user_id: str | None,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        outcome: str = "success",
        severity: str = "low",
        metadata: dict[str, Any] | None = None,
    ) -> PlatformEvent:
        return cls(
            id=str(uuid.uuid4()),
            operation=operation,
            actor_user_id=actor_user_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            severity=severity,
            created_at=datetime.now(tz=timezone.utc),
            metadata=metadata or {},
        )


__all__ = ["PlatformEvent"]
