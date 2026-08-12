from __future__ import annotations

from dataclasses import field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import field_validator, model_validator

from src.core.modules.project_management.domain.financials.configuration import BillingMethod
from src.core.modules.project_management.domain.identifiers import generate_id
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError
from src.core.platform.common.pydantic import (
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_required_text,
    validated_dataclass,
)
from src.core.platform.finance import (
    MONEY_STORAGE,
    PERCENTAGE_STORAGE,
    QUANTITY_STORAGE,
    RATE_STORAGE,
    CurrencyCode,
)


class BillingPreparationStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    DELIVERY_PENDING = "delivery_pending"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    RECONCILED = "reconciled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class BillableSourceType(str, Enum):
    APPROVED_TIME = "approved_time"
    POSTED_COST = "posted_cost"
    SCHEDULE_LINE = "schedule_line"
    ADJUSTMENT = "adjustment"


class BillingSourceLockStatus(str, Enum):
    RESERVED = "reserved"
    FINALIZED = "finalized"
    RELEASED = "released"


class BillingExternalEventType(str, Enum):
    DELIVERY_ACCEPTED = "delivery_accepted"
    DELIVERY_REJECTED = "delivery_rejected"
    STATUS_UPDATED = "status_updated"
    RECONCILED = "reconciled"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(value: object, *, code: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError("A valid timestamp is required.", code=code)
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _required(value: object, *, field_name: str, prefix: str) -> str:
    return normalize_required_text(
        value,
        message=f"{field_name.replace('_', ' ').title()} is required.",
        code=f"{prefix}_{field_name.upper()}_REQUIRED",
    )


@validated_dataclass
class ProjectBillingPreparation:
    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    billing_profile_id: str
    preparation_number: str
    billing_method: BillingMethod
    period_start: date
    period_end: date
    currency_code: str
    idempotency_key: str
    created_by: str
    status: BillingPreparationStatus = BillingPreparationStatus.DRAFT
    line_count: int = 0
    total_amount: Decimal = Decimal("0")
    correction_of_preparation_id: str | None = None
    approval_request_id: str | None = None
    submitted_by: str | None = None
    submitted_at: datetime | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejected_by: str | None = None
    rejected_at: datetime | None = None
    rejection_notes: str = ""
    delivery_requested_at: datetime | None = None
    delivered_at: datetime | None = None
    acknowledged_at: datetime | None = None
    reconciled_at: datetime | None = None
    row_version: int = 1
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    @field_validator(
        "id", "tenant_id", "organization_id", "project_id", "billing_profile_id",
        "preparation_number", "idempotency_key", "created_by", mode="before",
    )
    @classmethod
    def _required_fields(cls, value: object, info) -> str:
        return _required(value, field_name=info.field_name, prefix="BILLING_PREPARATION")

    @field_validator(
        "correction_of_preparation_id", "approval_request_id", "submitted_by",
        "approved_by", "rejected_by", mode="before",
    )
    @classmethod
    def _optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("rejection_notes", mode="before")
    @classmethod
    def _notes(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("currency_code", mode="before")
    @classmethod
    def _currency(cls, value: object) -> str:
        currency = CurrencyCode(str(value or ""))
        currency.minor_unit_quantum()
        return currency.code

    @field_validator("total_amount", mode="before")
    @classmethod
    def _total(cls, value: object) -> Decimal:
        return MONEY_STORAGE.validate(value)

    @field_validator("line_count", mode="before")
    @classmethod
    def _line_count(cls, value: object) -> int:
        count = int(value)
        if count < 0:
            raise ValidationError(
                "Billing preparation line count cannot be negative.",
                code="BILLING_PREPARATION_LINE_COUNT_INVALID",
            )
        return count

    @field_validator("row_version", mode="before")
    @classmethod
    def _version(cls, value: object) -> int:
        version = int(value)
        if version < 1:
            raise ValidationError(
                "Billing preparation version must be positive.",
                code="BILLING_PREPARATION_VERSION_INVALID",
            )
        return version

    @field_validator(
        "submitted_at", "approved_at", "rejected_at", "delivery_requested_at",
        "delivered_at", "acknowledged_at", "reconciled_at", mode="before",
    )
    @classmethod
    def _optional_timestamps(cls, value: object, info) -> datetime | None:
        if value is None:
            return None
        return _timestamp(value, code=f"BILLING_PREPARATION_{info.field_name.upper()}_INVALID")

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _timestamps(cls, value: object, info) -> datetime:
        return _timestamp(value, code=f"BILLING_PREPARATION_{info.field_name.upper()}_INVALID")

    @model_validator(mode="after")
    def _period_and_correction_shape(self) -> "ProjectBillingPreparation":
        if self.period_end < self.period_start:
            raise ValidationError(
                "Billing preparation period end cannot precede its start.",
                code="BILLING_PREPARATION_PERIOD_INVALID",
            )
        if self.total_amount < 0 and not self.correction_of_preparation_id:
            raise ValidationError(
                "A negative billing preparation must reference the preparation it corrects.",
                code="BILLING_PREPARATION_NEGATIVE_CORRECTION_REQUIRED",
            )
        return self

    def ensure_draft(self) -> None:
        if self.status is not BillingPreparationStatus.DRAFT:
            raise BusinessRuleError(
                "Only a draft billing preparation can be modified.",
                code="BILLING_PREPARATION_IMMUTABLE",
            )

    def replace_totals(
        self, *, line_count: int, total_amount: Decimal, occurred_at: datetime
    ) -> None:
        self.ensure_draft()
        self.line_count = line_count
        self.total_amount = total_amount
        self.updated_at = occurred_at

    def submit(
        self,
        *,
        submitted_by: str,
        submitted_at: datetime,
        approval_request_id: str | None = None,
    ) -> None:
        self.ensure_draft()
        if self.line_count < 1 or self.total_amount == 0:
            raise BusinessRuleError(
                "An empty billing preparation cannot be submitted.",
                code="BILLING_PREPARATION_EMPTY",
            )
        self.status = BillingPreparationStatus.SUBMITTED
        self.submitted_by = submitted_by
        self.submitted_at = submitted_at
        self.approval_request_id = approval_request_id
        self.updated_at = submitted_at

    def approve(self, *, approved_by: str, approved_at: datetime) -> None:
        if self.status is not BillingPreparationStatus.SUBMITTED:
            raise BusinessRuleError(
                "Only a submitted billing preparation can be approved.",
                code="BILLING_PREPARATION_APPROVAL_INVALID",
            )
        self.status = BillingPreparationStatus.APPROVED
        self.approved_by = approved_by
        self.approved_at = approved_at
        self.updated_at = approved_at

    def reject(self, *, rejected_by: str, rejected_at: datetime, notes: str = "") -> None:
        if self.status is not BillingPreparationStatus.SUBMITTED:
            raise BusinessRuleError(
                "Only a submitted billing preparation can be rejected.",
                code="BILLING_PREPARATION_REJECTION_INVALID",
            )
        self.status = BillingPreparationStatus.REJECTED
        self.rejected_by = rejected_by
        self.rejected_at = rejected_at
        self.rejection_notes = normalize_optional_text(notes)
        self.updated_at = rejected_at

    def request_delivery(self, *, occurred_at: datetime) -> None:
        if self.status is not BillingPreparationStatus.APPROVED:
            raise BusinessRuleError(
                "Only an approved billing preparation can be delivered.",
                code="BILLING_PREPARATION_DELIVERY_INVALID",
            )
        self.status = BillingPreparationStatus.DELIVERY_PENDING
        self.delivery_requested_at = occurred_at
        self.updated_at = occurred_at

    def mark_delivered(self, *, occurred_at: datetime) -> None:
        if self.status is not BillingPreparationStatus.DELIVERY_PENDING:
            raise BusinessRuleError(
                "Only a pending billing delivery can be marked delivered.",
                code="BILLING_PREPARATION_DELIVERED_INVALID",
            )
        self.status = BillingPreparationStatus.DELIVERED
        self.delivered_at = occurred_at
        self.updated_at = occurred_at

    def acknowledge(self, *, occurred_at: datetime) -> None:
        if self.status not in {
            BillingPreparationStatus.DELIVERY_PENDING,
            BillingPreparationStatus.DELIVERED,
        }:
            raise BusinessRuleError(
                "Only a delivered billing preparation can be acknowledged.",
                code="BILLING_PREPARATION_ACKNOWLEDGEMENT_INVALID",
            )
        self.status = BillingPreparationStatus.ACKNOWLEDGED
        self.acknowledged_at = occurred_at
        self.updated_at = occurred_at

    def reconcile(self, *, occurred_at: datetime) -> None:
        if self.status is not BillingPreparationStatus.ACKNOWLEDGED:
            raise BusinessRuleError(
                "Only an acknowledged billing preparation can be reconciled.",
                code="BILLING_PREPARATION_RECONCILIATION_INVALID",
            )
        self.status = BillingPreparationStatus.RECONCILED
        self.reconciled_at = occurred_at
        self.updated_at = occurred_at

    def cancel(self, *, occurred_at: datetime) -> None:
        self.ensure_draft()
        self.status = BillingPreparationStatus.CANCELLED
        self.updated_at = occurred_at

    @staticmethod
    def create(
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        billing_profile_id: str,
        preparation_number: str,
        billing_method: BillingMethod | str,
        period_start: date,
        period_end: date,
        currency_code: str,
        idempotency_key: str,
        created_by: str,
        created_at: datetime | None = None,
        **values,
    ) -> "ProjectBillingPreparation":
        now = created_at or _utc_now()
        return ProjectBillingPreparation(
            id=generate_id(),
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            billing_profile_id=billing_profile_id,
            preparation_number=preparation_number,
            billing_method=BillingMethod(billing_method),
            period_start=period_start,
            period_end=period_end,
            currency_code=currency_code,
            idempotency_key=idempotency_key,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            **values,
        )


@validated_dataclass
class ProjectBillingPreparationLine:
    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    preparation_id: str
    source_type: BillableSourceType
    source_id: str
    source_revision: str
    source_content_hash: str
    description: str
    source_date: date
    quantity: Decimal
    unit: str
    unit_rate: Decimal
    net_amount: Decimal
    currency_code: str
    task_id: str | None = None
    resource_id: str | None = None
    source_amount: Decimal | None = None
    markup_percent: Decimal | None = None
    rate_card_id: str | None = None
    rate_line_id: str | None = None
    rate_card_version: int | None = None
    created_at: datetime = field(default_factory=_utc_now)

    @field_validator(
        "id", "tenant_id", "organization_id", "project_id", "preparation_id",
        "source_id", "source_revision", mode="before",
    )
    @classmethod
    def _required_fields(cls, value: object, info) -> str:
        return _required(value, field_name=info.field_name, prefix="BILLING_LINE")

    @field_validator("description", "unit", mode="before")
    @classmethod
    def _required_text(cls, value: object, info) -> str:
        return _required(value, field_name=info.field_name, prefix="BILLING_LINE")

    @field_validator(
        "task_id", "resource_id", "rate_card_id", "rate_line_id", mode="before"
    )
    @classmethod
    def _optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("source_content_hash", mode="before")
    @classmethod
    def _source_hash(cls, value: object) -> str:
        normalized = str(value or "").strip().lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValidationError(
                "Billable source content hash must be SHA-256.",
                code="BILLING_LINE_SOURCE_HASH_INVALID",
            )
        return normalized

    @field_validator("quantity", mode="before")
    @classmethod
    def _quantity(cls, value: object) -> Decimal:
        quantity = QUANTITY_STORAGE.validate(value)
        if quantity == 0:
            raise ValidationError(
                "Billing line quantity cannot be zero.",
                code="BILLING_LINE_QUANTITY_INVALID",
            )
        return quantity

    @field_validator("unit_rate", mode="before")
    @classmethod
    def _unit_rate(cls, value: object) -> Decimal:
        return RATE_STORAGE.validate(value)

    @field_validator("net_amount", mode="before")
    @classmethod
    def _net_amount(cls, value: object) -> Decimal:
        amount = MONEY_STORAGE.validate(value)
        if amount == 0:
            raise ValidationError(
                "Billing line net amount cannot be zero.",
                code="BILLING_LINE_AMOUNT_INVALID",
            )
        return amount

    @field_validator("source_amount", mode="before")
    @classmethod
    def _source_amount(cls, value: object) -> Decimal | None:
        return None if value is None else MONEY_STORAGE.validate(value)

    @field_validator("markup_percent", mode="before")
    @classmethod
    def _markup(cls, value: object) -> Decimal | None:
        return None if value is None else PERCENTAGE_STORAGE.validate(value)

    @field_validator("currency_code", mode="before")
    @classmethod
    def _currency(cls, value: object) -> str:
        currency = CurrencyCode(str(value or ""))
        currency.minor_unit_quantum()
        return currency.code

    @field_validator("rate_card_version", mode="before")
    @classmethod
    def _rate_version(cls, value: object) -> int | None:
        if value is None:
            return None
        version = int(value)
        if version < 1:
            raise ValidationError(
                "Billing rate-card version must be positive.",
                code="BILLING_LINE_RATE_VERSION_INVALID",
            )
        return version

    @field_validator("created_at", mode="before")
    @classmethod
    def _created_at(cls, value: object) -> datetime:
        return _timestamp(value, code="BILLING_LINE_CREATED_AT_INVALID")

    @model_validator(mode="after")
    def _source_shape(self) -> "ProjectBillingPreparationLine":
        rate_fields = (self.rate_card_id, self.rate_line_id, self.rate_card_version)
        if any(value is not None for value in rate_fields) and not all(
            value is not None for value in rate_fields
        ):
            raise ValidationError(
                "Billing rate-card snapshot fields must be supplied together.",
                code="BILLING_LINE_RATE_SNAPSHOT_INCOMPLETE",
            )
        if self.source_type is BillableSourceType.APPROVED_TIME and not self.resource_id:
            raise ValidationError(
                "Approved-time billing requires a resource snapshot.",
                code="BILLING_LINE_RESOURCE_REQUIRED",
            )
        if self.source_type is BillableSourceType.POSTED_COST:
            if self.source_amount is None or self.markup_percent is None:
                raise ValidationError(
                    "Posted-cost billing requires source amount and markup snapshots.",
                    code="BILLING_LINE_COST_PLUS_SNAPSHOT_REQUIRED",
                )
        return self

    @staticmethod
    def create(**values) -> "ProjectBillingPreparationLine":
        return ProjectBillingPreparationLine(id=generate_id(), **values)


@validated_dataclass
class ProjectBillingSourceLock:
    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    source_type: BillableSourceType
    source_id: str
    source_revision: str
    source_content_hash: str
    preparation_id: str
    preparation_line_id: str
    status: BillingSourceLockStatus = BillingSourceLockStatus.RESERVED
    reserved_at: datetime = field(default_factory=_utc_now)
    finalized_at: datetime | None = None
    released_at: datetime | None = None

    @field_validator(
        "id", "tenant_id", "organization_id", "project_id", "source_id",
        "source_revision", "preparation_id", "preparation_line_id", mode="before",
    )
    @classmethod
    def _required_fields(cls, value: object, info) -> str:
        return _required(value, field_name=info.field_name, prefix="BILLING_SOURCE_LOCK")

    @field_validator("source_content_hash", mode="before")
    @classmethod
    def _source_hash(cls, value: object) -> str:
        normalized = str(value or "").strip().lower()
        if len(normalized) != 64 or any(char not in "0123456789abcdef" for char in normalized):
            raise ValidationError(
                "Billing source-lock hash must be SHA-256.",
                code="BILLING_SOURCE_LOCK_HASH_INVALID",
            )
        return normalized

    @field_validator("reserved_at", mode="before")
    @classmethod
    def _reserved_at(cls, value: object) -> datetime:
        return _timestamp(value, code="BILLING_SOURCE_LOCK_RESERVED_AT_INVALID")

    @field_validator("finalized_at", "released_at", mode="before")
    @classmethod
    def _optional_timestamps(cls, value: object, info) -> datetime | None:
        if value is None:
            return None
        return _timestamp(value, code=f"BILLING_SOURCE_LOCK_{info.field_name.upper()}_INVALID")

    def finalize(self, *, occurred_at: datetime) -> None:
        if self.status is not BillingSourceLockStatus.RESERVED:
            raise BusinessRuleError(
                "Only a reserved billing source can be finalized.",
                code="BILLING_SOURCE_LOCK_FINALIZE_INVALID",
            )
        self.status = BillingSourceLockStatus.FINALIZED
        self.finalized_at = occurred_at

    def release(self, *, occurred_at: datetime) -> None:
        if self.status is not BillingSourceLockStatus.RESERVED:
            raise BusinessRuleError(
                "Only a reserved billing source can be released.",
                code="BILLING_SOURCE_LOCK_RELEASE_INVALID",
            )
        self.status = BillingSourceLockStatus.RELEASED
        self.released_at = occurred_at

    @staticmethod
    def create(**values) -> "ProjectBillingSourceLock":
        return ProjectBillingSourceLock(id=generate_id(), **values)


@validated_dataclass(frozen=True)
class ProjectBillingExternalEvent:
    id: str
    tenant_id: str
    organization_id: str
    project_id: str
    preparation_id: str
    event_type: BillingExternalEventType
    external_system: str
    external_status: str
    idempotency_key: str
    occurred_at: datetime
    external_invoice_reference: str | None = None
    reconciliation_reference: str | None = None
    message: str = ""
    recorded_at: datetime = field(default_factory=_utc_now)

    @field_validator(
        "id", "tenant_id", "organization_id", "project_id", "preparation_id",
        "external_system", "external_status", "idempotency_key", mode="before",
    )
    @classmethod
    def _required_fields(cls, value: object, info) -> str:
        return _required(value, field_name=info.field_name, prefix="BILLING_EXTERNAL_EVENT")

    @field_validator(
        "external_invoice_reference", "reconciliation_reference", mode="before"
    )
    @classmethod
    def _optional_references(cls, value: object) -> str | None:
        normalized = normalize_optional_text(value)
        return normalized or None

    @field_validator("message", mode="before")
    @classmethod
    def _message(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("occurred_at", "recorded_at", mode="before")
    @classmethod
    def _timestamps(cls, value: object, info) -> datetime:
        return _timestamp(value, code=f"BILLING_EXTERNAL_EVENT_{info.field_name.upper()}_INVALID")

    @model_validator(mode="after")
    def _reconciliation_shape(self) -> "ProjectBillingExternalEvent":
        if (
            self.event_type is BillingExternalEventType.RECONCILED
            and not self.reconciliation_reference
        ):
            raise ValidationError(
                "A reconciled billing event requires a reconciliation reference.",
                code="BILLING_EXTERNAL_EVENT_RECONCILIATION_REQUIRED",
            )
        return self

    @staticmethod
    def create(**values) -> "ProjectBillingExternalEvent":
        return ProjectBillingExternalEvent(id=generate_id(), **values)


__all__ = [
    "BillableSourceType",
    "BillingExternalEventType",
    "BillingPreparationStatus",
    "BillingSourceLockStatus",
    "ProjectBillingExternalEvent",
    "ProjectBillingPreparation",
    "ProjectBillingPreparationLine",
    "ProjectBillingSourceLock",
]
