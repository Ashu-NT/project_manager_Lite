from __future__ import annotations

from dataclasses import field
from datetime import datetime, timezone
from enum import Enum

from pydantic import field_validator, model_validator

from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.integration.events import IntegrationEventEnvelope


class OutboxDeliveryStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    RETRY = "retry"
    PUBLISHED = "published"
    DEAD_LETTER = "dead_letter"


class InboxProcessingStatus(str, Enum):
    PROCESSING = "processing"
    RETRY = "retry"
    PROCESSED = "processed"
    QUARANTINED = "quarantined"
    DEAD_LETTER = "dead_letter"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _aware_utc(value: object, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError(
            f"{field_name.replace('_', ' ').title()} must be a timestamp.",
            code="INTEGRATION_DELIVERY_TIMESTAMP_INVALID",
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError(
            f"{field_name.replace('_', ' ').title()} must include a timezone.",
            code="INTEGRATION_DELIVERY_TIMESTAMP_TIMEZONE_REQUIRED",
        )
    return value.astimezone(timezone.utc)


def _required(value: object, *, field_name: str) -> str:
    return normalize_required_text(
        value,
        message=f"{field_name.replace('_', ' ').title()} is required.",
        code=f"INTEGRATION_{field_name.upper()}_REQUIRED",
    )


@validated_dataclass
class IntegrationOutboxRecord:
    id: str
    owner_module: str
    envelope: IntegrationEventEnvelope
    status: OutboxDeliveryStatus = OutboxDeliveryStatus.PENDING
    attempt_count: int = 0
    max_attempts: int = 8
    available_at: datetime = field(default_factory=_utc_now)
    lease_token: str | None = None
    lease_expires_at: datetime | None = None
    published_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    row_version: int = 1

    @field_validator("id", "owner_module", mode="before")
    @classmethod
    def _validate_required(cls, value: object, info) -> str:
        return _required(value, field_name=info.field_name)

    @field_validator(
        "lease_token", "last_error_code", "last_error_message", mode="before"
    )
    @classmethod
    def _normalize_optional(cls, value: object) -> str | None:
        normalized = normalize_optional_text(value)
        return normalized or None

    @field_validator("attempt_count", mode="before")
    @classmethod
    def _validate_attempt_count(cls, value: object) -> int:
        resolved = int(value or 0)
        if resolved < 0:
            raise ValidationError(
                "Outbox attempt count cannot be negative.",
                code="INTEGRATION_OUTBOX_ATTEMPT_INVALID",
            )
        return resolved

    @field_validator("max_attempts", "row_version", mode="before")
    @classmethod
    def _validate_positive(cls, value: object, info) -> int:
        resolved = int(value or 0)
        if resolved < 1:
            raise ValidationError(
                f"{info.field_name.replace('_', ' ').title()} must be positive.",
                code="INTEGRATION_DELIVERY_VERSION_INVALID",
            )
        return resolved

    @field_validator(
        "available_at", "lease_expires_at", "published_at", "created_at", "updated_at",
        mode="before",
    )
    @classmethod
    def _normalize_timestamps(cls, value: object, info) -> datetime | None:
        if value is None:
            return None
        return _aware_utc(value, field_name=info.field_name)

    @model_validator(mode="after")
    def _validate_state(self) -> IntegrationOutboxRecord:
        if self.envelope.organization_id is None:
            raise ValidationError(
                "Financial integration events require organization scope.",
                code="INTEGRATION_ORGANIZATION_REQUIRED",
            )
        if self.envelope.aggregate_version < 1:
            raise ValidationError(
                "Durable integration events require a positive aggregate version.",
                code="INTEGRATION_AGGREGATE_VERSION_INVALID",
            )
        if self.attempt_count > self.max_attempts:
            raise ValidationError(
                "Outbox attempt count cannot exceed maximum attempts.",
                code="INTEGRATION_OUTBOX_ATTEMPT_INVALID",
            )
        if self.status == OutboxDeliveryStatus.CLAIMED and (
            not self.lease_token or self.lease_expires_at is None
        ):
            raise ValidationError(
                "Claimed outbox records require a lease token and expiry.",
                code="INTEGRATION_OUTBOX_LEASE_REQUIRED",
            )
        if self.status != OutboxDeliveryStatus.CLAIMED and (
            self.lease_token is not None or self.lease_expires_at is not None
        ):
            raise ValidationError(
                "Only claimed outbox records may retain lease metadata.",
                code="INTEGRATION_OUTBOX_LEASE_INVALID",
            )
        if (self.status == OutboxDeliveryStatus.PUBLISHED) != (self.published_at is not None):
            raise ValidationError(
                "Published outbox records require exactly one publication timestamp.",
                code="INTEGRATION_OUTBOX_PUBLISHED_STATE_INVALID",
            )
        return self

    @property
    def tenant_id(self) -> str:
        return self.envelope.tenant_id

    @property
    def organization_id(self) -> str:
        return str(self.envelope.organization_id)

    def require_lease(self, lease_token: str, *, at: datetime | None = None) -> None:
        expired = bool(at and self.lease_expires_at and self.lease_expires_at <= at)
        if self.status != OutboxDeliveryStatus.CLAIMED or self.lease_token != lease_token or expired:
            raise BusinessRuleError(
                "Outbox lease is missing, expired, or owned by another worker.",
                code="INTEGRATION_OUTBOX_LEASE_MISMATCH",
            )


@validated_dataclass
class IntegrationInboxReceipt:
    id: str
    consumer_name: str
    envelope: IntegrationEventEnvelope
    deduplication_key: str
    status: InboxProcessingStatus = InboxProcessingStatus.PROCESSING
    attempt_count: int = 1
    max_attempts: int = 8
    available_at: datetime = field(default_factory=_utc_now)
    lease_token: str | None = None
    lease_expires_at: datetime | None = None
    processed_at: datetime | None = None
    quarantine_reason_code: str | None = None
    conflicting_envelope: IntegrationEventEnvelope | None = None
    conflict_detected_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    row_version: int = 1

    @field_validator("id", "consumer_name", "deduplication_key", mode="before")
    @classmethod
    def _validate_required(cls, value: object, info) -> str:
        return _required(value, field_name=info.field_name)

    @field_validator(
        "lease_token", "quarantine_reason_code", "last_error_code", "last_error_message",
        mode="before",
    )
    @classmethod
    def _normalize_optional(cls, value: object) -> str | None:
        normalized = normalize_optional_text(value)
        return normalized or None

    @field_validator("attempt_count", "max_attempts", "row_version", mode="before")
    @classmethod
    def _validate_positive(cls, value: object, info) -> int:
        resolved = int(value or 0)
        if resolved < 1:
            raise ValidationError(
                f"{info.field_name.replace('_', ' ').title()} must be positive.",
                code="INTEGRATION_DELIVERY_VERSION_INVALID",
            )
        return resolved

    @field_validator(
        "available_at", "lease_expires_at", "processed_at", "conflict_detected_at", "created_at", "updated_at",
        mode="before",
    )
    @classmethod
    def _normalize_timestamps(cls, value: object, info) -> datetime | None:
        if value is None:
            return None
        return _aware_utc(value, field_name=info.field_name)

    @model_validator(mode="after")
    def _validate_state(self) -> IntegrationInboxReceipt:
        if self.envelope.organization_id is None:
            raise ValidationError(
                "Financial integration receipts require organization scope.",
                code="INTEGRATION_ORGANIZATION_REQUIRED",
            )
        if self.envelope.aggregate_version < 1:
            raise ValidationError(
                "Durable integration events require a positive aggregate version.",
                code="INTEGRATION_AGGREGATE_VERSION_INVALID",
            )
        if self.deduplication_key != self.envelope.inbox_deduplication_key(
            self.consumer_name
        ):
            raise ValidationError(
                "Inbox deduplication key does not match its consumer and event identity.",
                code="INTEGRATION_INBOX_DEDUPLICATION_KEY_INVALID",
            )
        if self.attempt_count > self.max_attempts:
            raise ValidationError(
                "Inbox attempt count cannot exceed maximum attempts.",
                code="INTEGRATION_INBOX_ATTEMPT_INVALID",
            )
        if self.status == InboxProcessingStatus.PROCESSING and (
            (self.lease_token is None) != (self.lease_expires_at is None)
        ):
            raise ValidationError(
                "Inbox lease token and expiry must be supplied together.",
                code="INTEGRATION_INBOX_LEASE_INVALID",
            )
        if self.status != InboxProcessingStatus.PROCESSING and (
            self.lease_token is not None or self.lease_expires_at is not None
        ):
            raise ValidationError(
                "Only processing inbox receipts may retain lease metadata.",
                code="INTEGRATION_INBOX_LEASE_INVALID",
            )
        if self.status == InboxProcessingStatus.PROCESSED and self.processed_at is None:
            raise ValidationError(
                "Processed inbox receipts require a completion timestamp.",
                code="INTEGRATION_INBOX_PROCESSED_STATE_INVALID",
            )
        if self.status in {
            InboxProcessingStatus.PROCESSING,
            InboxProcessingStatus.RETRY,
        } and self.processed_at is not None:
            raise ValidationError(
                "Pending inbox work cannot already have completion evidence.",
                code="INTEGRATION_INBOX_PROCESSED_STATE_INVALID",
            )
        if (self.status == InboxProcessingStatus.QUARANTINED) != (
            self.quarantine_reason_code is not None
        ):
            raise ValidationError(
                "Quarantined inbox receipts require exactly one reason code.",
                code="INTEGRATION_INBOX_QUARANTINE_STATE_INVALID",
            )
        if (self.conflicting_envelope is None) != (self.conflict_detected_at is None):
            raise ValidationError(
                "Conflicting envelope evidence and detection time must be retained together.",
                code="INTEGRATION_INBOX_CONFLICT_EVIDENCE_INVALID",
            )
        if self.conflicting_envelope is not None:
            conflict = self.conflicting_envelope
            if (
                self.status != InboxProcessingStatus.QUARANTINED
                or conflict.event_id != self.envelope.event_id
                or conflict.tenant_id != self.envelope.tenant_id
                or conflict.envelope_hash == self.envelope.envelope_hash
            ):
                raise ValidationError(
                    "Inbox conflict evidence must preserve a different envelope for the same scoped event identity.",
                    code="INTEGRATION_INBOX_CONFLICT_EVIDENCE_INVALID",
                )
        return self

    @property
    def tenant_id(self) -> str:
        return self.envelope.tenant_id

    @property
    def organization_id(self) -> str:
        return str(self.envelope.organization_id)


__all__ = [
    "InboxProcessingStatus",
    "IntegrationInboxReceipt",
    "IntegrationOutboxRecord",
    "OutboxDeliveryStatus",
]
