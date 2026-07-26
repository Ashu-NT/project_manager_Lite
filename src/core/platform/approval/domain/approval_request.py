from __future__ import annotations

from collections.abc import Mapping
from dataclasses import field
from datetime import datetime, timezone
from typing import Any

from pydantic import field_validator

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.approval.domain.approval_state import ApprovalStatus
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)


def _normalize_optional_datetime(value: object, *, code: str) -> datetime | None:
    if value in (None, ""):
        return None
    if not isinstance(value, datetime):
        raise ValidationError(
            "Approval timestamps must be valid datetimes.",
            code=code,
        )
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_required_datetime(value: object, *, code: str) -> datetime:
    normalized = _normalize_optional_datetime(value, code=code)
    if normalized is None:
        raise ValidationError(
            "Approval request timestamp is required.",
            code=code,
        )
    return normalized


def _normalize_status(value: ApprovalStatus | str | None) -> ApprovalStatus:
    if isinstance(value, ApprovalStatus):
        return value
    raw = normalize_optional_text(value)
    if "." in raw:
        raw = raw.rsplit(".", 1)[-1]
    raw = raw.upper() or ApprovalStatus.PENDING.value
    try:
        return ApprovalStatus(raw)
    except ValueError as exc:
        raise ValidationError(
            "Approval request status is invalid.",
            code="APPROVAL_STATUS_INVALID",
        ) from exc


def _normalize_payload(value: object) -> dict[str, Any]:
    if value in (None, ""):
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    raise ValidationError(
        "Approval payload must be a dictionary.",
        code="APPROVAL_PAYLOAD_INVALID",
    )


@validated_dataclass
class ApprovalRequest:
    id: str
    request_type: str
    entity_type: str
    entity_id: str
    project_id: str | None
    payload: dict[str, Any]
    organization_id: str | None = None
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_by_user_id: str | None = None
    requested_by_username: str | None = None
    requested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    decided_by_user_id: str | None = None
    decided_by_username: str | None = None
    decided_at: datetime | None = None
    decision_note: str | None = None

    @field_validator("request_type", mode="before")
    @classmethod
    def _validate_request_type(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Approval request type is required.",
            code="APPROVAL_REQUEST_TYPE_REQUIRED",
        ).lower()

    @field_validator("entity_type", mode="before")
    @classmethod
    def _validate_entity_type(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Approval entity type is required.",
            code="APPROVAL_ENTITY_TYPE_REQUIRED",
        ).lower()

    @field_validator("entity_id", mode="before")
    @classmethod
    def _validate_entity_id(cls, value: object) -> str:
        return normalize_required_text(
            value,
            message="Approval entity ID is required.",
            code="APPROVAL_ENTITY_ID_REQUIRED",
        )

    @field_validator(
        "project_id",
        "organization_id",
        "requested_by_user_id",
        "decided_by_user_id",
        mode="before",
    )
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("requested_by_username", "decided_by_username", "decision_note", mode="before")
    @classmethod
    def _normalize_optional_text_fields(cls, value: object) -> str | None:
        normalized = normalize_optional_text(value)
        return normalized or None

    @field_validator("payload", mode="before")
    @classmethod
    def _validate_payload(cls, value: object) -> dict[str, Any]:
        return _normalize_payload(value)

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: ApprovalStatus | str | None) -> ApprovalStatus:
        return _normalize_status(value)

    @field_validator("requested_at", mode="before")
    @classmethod
    def _validate_requested_at(cls, value: object) -> datetime:
        return _normalize_required_datetime(
            value,
            code="APPROVAL_REQUESTED_AT_INVALID",
        )

    @field_validator("decided_at", mode="before")
    @classmethod
    def _validate_decided_at(cls, value: object) -> datetime | None:
        return _normalize_optional_datetime(
            value,
            code="APPROVAL_DECIDED_AT_INVALID",
        )

    @staticmethod
    def create(
        request_type: str,
        entity_type: str,
        entity_id: str,
        *,
        project_id: str | None,
        organization_id: str | None = None,
        payload: dict[str, Any] | None = None,
        requested_by_user_id: str | None = None,
        requested_by_username: str | None = None,
    ) -> "ApprovalRequest":
        return ApprovalRequest(
            id=generate_id(),
            request_type=request_type,
            entity_type=entity_type,
            entity_id=entity_id,
            project_id=project_id,
            payload=payload,
            organization_id=organization_id,
            requested_by_user_id=requested_by_user_id,
            requested_by_username=requested_by_username,
        )


__all__ = ["ApprovalRequest"]
