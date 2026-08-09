from __future__ import annotations

from datetime import datetime, timezone

from pydantic import AwareDatetime, BaseModel, ConfigDict, JsonValue, field_validator

from src.core.platform.integration.canonical_json import canonical_json_sha256


def _required_text(value: object, *, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{label} is required")
    return normalized


class IntegrationEventEnvelope(BaseModel):
    """Transport-neutral envelope for durable, at-least-once integration delivery."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    event_type: str
    schema_version: int
    tenant_id: str
    organization_id: str | None = None
    aggregate_type: str
    aggregate_id: str
    aggregate_version: int
    occurred_at: AwareDatetime
    correlation_id: str | None = None
    causation_id: str | None = None
    payload: dict[str, JsonValue]

    @field_validator(
        "event_id",
        "event_type",
        "tenant_id",
        "aggregate_type",
        "aggregate_id",
        mode="before",
    )
    @classmethod
    def _validate_required_text(cls, value: object, info) -> str:
        return _required_text(value, label=info.field_name.replace("_", " ").capitalize())

    @field_validator("organization_id", "correlation_id", "causation_id", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: object) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    @field_validator("schema_version", mode="before")
    @classmethod
    def _validate_schema_version(cls, value: object) -> int:
        resolved = int(value)
        if resolved < 1:
            raise ValueError("Schema version must be positive")
        return resolved

    @field_validator("aggregate_version", mode="before")
    @classmethod
    def _validate_aggregate_version(cls, value: object) -> int:
        resolved = int(value)
        if resolved < 0:
            raise ValueError("Aggregate version cannot be negative")
        return resolved

    @field_validator("occurred_at", mode="after")
    @classmethod
    def _normalize_occurred_at(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)

    @property
    def payload_hash(self) -> str:
        return canonical_json_sha256(self.payload)

    @property
    def envelope_hash(self) -> str:
        """Hash every immutable transport fact for conflicting-event detection."""

        return canonical_json_sha256(self.model_dump(mode="json"))

    def inbox_deduplication_key(self, consumer_name: str) -> str:
        consumer = _required_text(consumer_name, label="Consumer name")
        identity = {
            "consumer": consumer,
            "tenant_id": self.tenant_id,
            "event_id": self.event_id,
        }
        return f"inbox:v1:{canonical_json_sha256(identity)}"


__all__ = ["IntegrationEventEnvelope"]
