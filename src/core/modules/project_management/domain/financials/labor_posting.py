from __future__ import annotations

from dataclasses import field
from datetime import date, datetime, timezone
from decimal import Decimal

from pydantic import field_validator

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.pydantic import normalize_optional_identifier, normalize_required_text, validated_dataclass
from src.core.platform.finance import MONEY_STORAGE, QUANTITY_STORAGE, CurrencyCode


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@validated_dataclass
class ApprovedTimeLaborPosting:
    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    time_entry_id: str
    source_revision: int
    source_content_hash: str
    approved_snapshot_id: str
    timesheet_period_id: str
    actual_cost_entry_id: str
    hours: Decimal
    work_date: date
    rate_amount: Decimal
    rate_currency: str
    rate_card_id: str
    rate_line_id: str
    rate_card_version: int
    rate_precedence_level: int
    rate_effective_date: date
    rate_resolved_at: datetime
    approved_at: datetime
    resource_id: str
    task_id: str | None = None
    employee_id: str | None = None
    reversal_cost_entry_id: str | None = None
    created_at: datetime = field(default_factory=_utc_now)

    @field_validator(
        "id", "tenant_id", "organization_id", "project_id", "time_entry_id",
        "approved_snapshot_id", "timesheet_period_id", "actual_cost_entry_id",
        "rate_card_id", "rate_line_id", "resource_id", mode="before",
    )
    @classmethod
    def _required(cls, value: object, info) -> str:
        return normalize_required_text(value, message=f"{info.field_name} is required.", code="LABOR_POSTING_ID_REQUIRED")

    @field_validator("task_id", "employee_id", "reversal_cost_entry_id", mode="before")
    @classmethod
    def _optional_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("hours", mode="before")
    @classmethod
    def _hours(cls, value: object) -> Decimal:
        amount = QUANTITY_STORAGE.validate(value)
        if amount <= 0:
            raise ValidationError("Approved labor hours must be positive.", code="LABOR_POSTING_HOURS_INVALID")
        return amount

    @field_validator("rate_amount", mode="before")
    @classmethod
    def _rate(cls, value: object) -> Decimal:
        amount = MONEY_STORAGE.validate(value)
        if amount < 0:
            raise ValidationError("Approved labor rate cannot be negative.", code="LABOR_POSTING_RATE_INVALID")
        return amount

    @field_validator("rate_currency", mode="before")
    @classmethod
    def _currency(cls, value: object) -> str:
        return CurrencyCode(str(value or "")).code

    @field_validator("source_revision", "rate_card_version", "rate_precedence_level", mode="before")
    @classmethod
    def _positive(cls, value: object, info) -> int:
        resolved = int(value)
        if resolved < 1:
            raise ValidationError(f"{info.field_name} must be positive.", code="LABOR_POSTING_VERSION_INVALID")
        return resolved

    @field_validator("rate_resolved_at", "approved_at", "created_at", mode="before")
    @classmethod
    def _timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @field_validator("source_content_hash", mode="before")
    @classmethod
    def _hash(cls, value: object) -> str:
        normalized = str(value or "").strip().lower()
        if len(normalized) != 64 or any(c not in "0123456789abcdef" for c in normalized):
            raise ValidationError("Labor source hash must be SHA-256.", code="LABOR_POSTING_HASH_INVALID")
        return normalized


__all__ = ["ApprovedTimeLaborPosting"]
