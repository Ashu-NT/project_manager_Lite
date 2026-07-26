from __future__ import annotations

from collections.abc import Mapping
from dataclasses import field
from datetime import datetime, timezone

from pydantic import field_validator

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    validated_dataclass,
)

RUNTIME_EXECUTION_STATUS_RUNNING = "RUNNING"
RUNTIME_EXECUTION_STATUS_COMPLETED = "COMPLETED"
RUNTIME_EXECUTION_STATUS_FAILED = "FAILED"
RUNTIME_EXECUTION_STATUS_CANCELLED = "CANCELLED"
RUNTIME_EXECUTION_STATUS_CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED"

VALID_RUNTIME_EXECUTION_STATUSES: frozenset[str] = frozenset(
    {
        RUNTIME_EXECUTION_STATUS_RUNNING,
        RUNTIME_EXECUTION_STATUS_COMPLETED,
        RUNTIME_EXECUTION_STATUS_FAILED,
        RUNTIME_EXECUTION_STATUS_CANCELLED,
        RUNTIME_EXECUTION_STATUS_CANCELLATION_REQUESTED,
    }
)


def _normalize_optional_datetime(value: object, *, code: str) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, datetime):
        raise ValidationError(
            "Runtime execution timestamps must be valid datetimes.",
            code=code,
        )
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_optional_scalar_text(value: object) -> str | None:
    normalized = normalize_optional_text(value)
    return normalized or None


def _normalize_metadata(value: object) -> dict[str, object]:
    if value in (None, ""):
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    raise ValidationError(
        "Runtime execution metadata must be a dictionary.",
        code="RUNTIME_EXECUTION_METADATA_INVALID",
    )


def _normalize_non_negative_int(
    value: object,
    *,
    code: str,
    message: str,
    default: int,
) -> int:
    try:
        resolved = int(value if value not in (None, "") else default)
    except (TypeError, ValueError) as exc:
        raise ValidationError(message, code=code) from exc
    if resolved < 0:
        raise ValidationError(message, code=code)
    return resolved


def _normalize_positive_int(
    value: object,
    *,
    code: str,
    message: str,
    default: int,
) -> int:
    try:
        resolved = int(value if value not in (None, "") else default)
    except (TypeError, ValueError) as exc:
        raise ValidationError(message, code=code) from exc
    if resolved < 1:
        raise ValidationError(message, code=code)
    return resolved


def _normalize_status(value: object) -> str:
    normalized = normalize_optional_text(value).upper() or RUNTIME_EXECUTION_STATUS_RUNNING
    if normalized not in VALID_RUNTIME_EXECUTION_STATUSES:
        raise ValidationError(
            "Runtime execution status is invalid.",
            code="RUNTIME_EXECUTION_STATUS_INVALID",
        )
    return normalized


@validated_dataclass
class RuntimeExecution:
    id: str
    operation_type: str
    operation_key: str
    module_code: str
    status: str
    requested_by_user_id: str | None = None
    requested_by_username: str | None = None
    input_path: str | None = None
    output_path: str | None = None
    output_file_name: str | None = None
    output_media_type: str | None = None
    output_metadata: dict[str, object] = field(default_factory=dict)
    created_count: int = 0
    updated_count: int = 0
    error_count: int = 0
    error_message: str | None = None
    cancellation_requested_at: datetime | None = None
    cancellation_requested_by_user_id: str | None = None
    cancellation_requested_by_username: str | None = None
    retry_of_execution_id: str | None = None
    attempt_number: int = 1
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("operation_type", mode="before")
    @classmethod
    def _normalize_operation_type(cls, value: object) -> str:
        return normalize_optional_text(value).lower() or "runtime"

    @field_validator("operation_key", mode="before")
    @classmethod
    def _normalize_operation_key(cls, value: object) -> str:
        return normalize_optional_text(value) or "operation"

    @field_validator("module_code", mode="before")
    @classmethod
    def _normalize_module_code(cls, value: object) -> str:
        return normalize_optional_text(value).lower() or "platform"

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> str:
        return _normalize_status(value)

    @field_validator(
        "requested_by_user_id",
        "cancellation_requested_by_user_id",
        "retry_of_execution_id",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("requested_by_username", "cancellation_requested_by_username", "output_file_name", "error_message", mode="before")
    @classmethod
    def _normalize_optional_text_fields(cls, value: object) -> str | None:
        return _normalize_optional_scalar_text(value)

    @field_validator("output_media_type", mode="before")
    @classmethod
    def _normalize_output_media_type(cls, value: object) -> str | None:
        normalized = normalize_optional_text(value).lower()
        return normalized or None

    @field_validator("input_path", "output_path", mode="before")
    @classmethod
    def _normalize_optional_paths(cls, value: object) -> str | None:
        return _normalize_optional_scalar_text(value)

    @field_validator("output_metadata", mode="before")
    @classmethod
    def _validate_output_metadata(cls, value: object) -> dict[str, object]:
        return _normalize_metadata(value)

    @field_validator("created_count", mode="before")
    @classmethod
    def _validate_created_count(cls, value: object) -> int:
        return _normalize_non_negative_int(
            value,
            code="RUNTIME_EXECUTION_CREATED_COUNT_INVALID",
            message="Runtime created count cannot be negative.",
            default=0,
        )

    @field_validator("updated_count", mode="before")
    @classmethod
    def _validate_updated_count(cls, value: object) -> int:
        return _normalize_non_negative_int(
            value,
            code="RUNTIME_EXECUTION_UPDATED_COUNT_INVALID",
            message="Runtime updated count cannot be negative.",
            default=0,
        )

    @field_validator("error_count", mode="before")
    @classmethod
    def _validate_error_count(cls, value: object) -> int:
        return _normalize_non_negative_int(
            value,
            code="RUNTIME_EXECUTION_ERROR_COUNT_INVALID",
            message="Runtime error count cannot be negative.",
            default=0,
        )

    @field_validator("attempt_number", mode="before")
    @classmethod
    def _validate_attempt_number(cls, value: object) -> int:
        return _normalize_positive_int(
            value,
            code="RUNTIME_EXECUTION_ATTEMPT_INVALID",
            message="Runtime attempt number must be positive.",
            default=1,
        )

    @field_validator(
        "cancellation_requested_at",
        "started_at",
        "completed_at",
        "created_at",
        "updated_at",
        mode="before",
    )
    @classmethod
    def _validate_optional_datetimes(cls, value: object) -> datetime | None:
        return _normalize_optional_datetime(
            value,
            code="RUNTIME_EXECUTION_TIMESTAMP_INVALID",
        )

    @staticmethod
    def create(
        *,
        operation_type: str,
        operation_key: str,
        module_code: str,
        requested_by_user_id: str | None = None,
        requested_by_username: str | None = None,
        input_path: str | None = None,
        output_path: str | None = None,
        retry_of_execution_id: str | None = None,
        attempt_number: int = 1,
    ) -> "RuntimeExecution":
        now = datetime.now(timezone.utc)
        return RuntimeExecution(
            id=generate_id(),
            operation_type=operation_type,
            operation_key=operation_key,
            module_code=module_code,
            status=RUNTIME_EXECUTION_STATUS_RUNNING,
            requested_by_user_id=requested_by_user_id,
            requested_by_username=requested_by_username,
            input_path=input_path,
            output_path=output_path,
            output_file_name=None,
            output_media_type=None,
            output_metadata={},
            started_at=now,
            completed_at=None,
            cancellation_requested_at=None,
            cancellation_requested_by_user_id=None,
            cancellation_requested_by_username=None,
            retry_of_execution_id=retry_of_execution_id,
            attempt_number=attempt_number,
            created_at=now,
            updated_at=now,
        )


__all__ = ["RuntimeExecution"]
