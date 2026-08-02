from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Generic, Literal, Protocol, TypeVar

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator, model_validator

from src.core.platform.finance.money.serialization import (
    DecimalQuantityPayload,
    MonetaryRatePayload,
)
from src.core.platform.integration.canonical_json import canonical_json_sha256


class FinancialSourceModule(str, Enum):
    PROJECT_MANAGEMENT = "project_management"
    PLATFORM_TIME = "platform_time"
    INVENTORY_PROCUREMENT = "inventory_procurement"
    DATA_EXCHANGE = "data_exchange"


class FinancialSourceType(str, Enum):
    TIME_ENTRY = "time_entry"
    PURCHASE_ORDER_LINE = "purchase_order_line"
    RECEIPT_LINE = "receipt_line"
    MANUAL_COMMAND = "manual_command"
    IMPORT_ROW = "import_row"


class FinancialPostingPurpose(str, Enum):
    LABOR_ACTUAL = "labor_actual"
    PURCHASE_COMMITMENT = "purchase_commitment"
    RECEIPT_ACCRUAL = "receipt_accrual"
    MANUAL_ACTUAL = "manual_actual"
    LEGACY_MIGRATION = "legacy_migration"


_ALLOWED_SOURCE_COMBINATIONS = {
    (
        FinancialSourceModule.PLATFORM_TIME,
        FinancialSourceType.TIME_ENTRY,
        FinancialPostingPurpose.LABOR_ACTUAL,
    ),
    (
        FinancialSourceModule.INVENTORY_PROCUREMENT,
        FinancialSourceType.PURCHASE_ORDER_LINE,
        FinancialPostingPurpose.PURCHASE_COMMITMENT,
    ),
    (
        FinancialSourceModule.INVENTORY_PROCUREMENT,
        FinancialSourceType.RECEIPT_LINE,
        FinancialPostingPurpose.RECEIPT_ACCRUAL,
    ),
    (
        FinancialSourceModule.PROJECT_MANAGEMENT,
        FinancialSourceType.MANUAL_COMMAND,
        FinancialPostingPurpose.MANUAL_ACTUAL,
    ),
    (
        FinancialSourceModule.DATA_EXCHANGE,
        FinancialSourceType.IMPORT_ROW,
        FinancialPostingPurpose.LEGACY_MIGRATION,
    ),
}


def _required_text(value: object, *, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{label} is required")
    return normalized


class _FinancialSourceContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FinancialSourceReference(_FinancialSourceContract):
    """Scoped semantic identity used independently of message delivery identity."""

    tenant_id: str
    organization_id: str
    project_id: str
    source_module: FinancialSourceModule
    source_type: FinancialSourceType
    source_id: str
    source_line_id: str | None = None
    source_revision: str
    content_hash: str
    posting_purpose: FinancialPostingPurpose

    @field_validator(
        "tenant_id",
        "organization_id",
        "project_id",
        "source_id",
        "source_revision",
        mode="before",
    )
    @classmethod
    def _validate_required_text(cls, value: object, info) -> str:
        return _required_text(value, label=info.field_name.replace("_", " ").capitalize())

    @field_validator("source_line_id", mode="before")
    @classmethod
    def _normalize_source_line_id(cls, value: object) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    @field_validator("content_hash", mode="before")
    @classmethod
    def _validate_content_hash(cls, value: object) -> str:
        normalized = str(value or "").strip().lower()
        if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("Content hash must be a lowercase SHA-256 digest")
        return normalized

    @model_validator(mode="after")
    def _validate_source_combination(self) -> "FinancialSourceReference":
        combination = (self.source_module, self.source_type, self.posting_purpose)
        if combination not in _ALLOWED_SOURCE_COMBINATIONS:
            raise ValueError("Source module, type, and posting purpose are incompatible")
        if self.source_type in {
            FinancialSourceType.PURCHASE_ORDER_LINE,
            FinancialSourceType.RECEIPT_LINE,
            FinancialSourceType.IMPORT_ROW,
        } and not self.source_line_id:
            raise ValueError("Line-based financial sources require a source line ID")
        return self

    @property
    def idempotency_key(self) -> str:
        # Project and content are excluded so a conflicting reassignment/replay
        # collides with the original semantic source and can be quarantined.
        identity = {
            "tenant_id": self.tenant_id,
            "organization_id": self.organization_id,
            "source_module": self.source_module.value,
            "source_type": self.source_type.value,
            "source_id": self.source_id,
            "source_line_id": self.source_line_id,
            "source_revision": self.source_revision,
            "posting_purpose": self.posting_purpose.value,
        }
        return f"pfin:v1:{canonical_json_sha256(identity)}"


def financial_source_content_hash(payload: BaseModel | Mapping[str, object]) -> str:
    """Hash the immutable source snapshot body before constructing its reference."""

    return canonical_json_sha256(payload)


class ApprovedTimeFinancialSource(_FinancialSourceContract):
    reference: FinancialSourceReference
    approval_status: Literal["APPROVED"] = "APPROVED"
    approved_snapshot_id: str
    timesheet_period_id: str
    time_entry_id: str
    work_allocation_id: str
    resource_id: str
    employee_id: str | None = None
    assignment_id: str | None = None
    task_id: str | None = None
    work_date: date
    approved_at: AwareDatetime
    hours: DecimalQuantityPayload
    correction_of_revision: str | None = None

    @field_validator(
        "approved_snapshot_id",
        "timesheet_period_id",
        "time_entry_id",
        "work_allocation_id",
        "resource_id",
        mode="before",
    )
    @classmethod
    def _validate_required_text(cls, value: object, info) -> str:
        return _required_text(value, label=info.field_name.replace("_", " ").capitalize())

    @field_validator("employee_id", "assignment_id", "task_id", "correction_of_revision", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: object) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    @field_validator("approved_at", mode="after")
    @classmethod
    def _normalize_approved_at(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _validate_time_source(self) -> "ApprovedTimeFinancialSource":
        reference = self.reference
        if (
            reference.source_module != FinancialSourceModule.PLATFORM_TIME
            or reference.source_type != FinancialSourceType.TIME_ENTRY
            or reference.posting_purpose != FinancialPostingPurpose.LABOR_ACTUAL
        ):
            raise ValueError("Approved Time source reference is incompatible")
        if reference.source_id != self.time_entry_id:
            raise ValueError("Time entry ID must match the source reference")
        if self.hours.unit != "HOUR" or Decimal(self.hours.value) <= 0:
            raise ValueError("Approved Time hours must be a positive HOUR quantity")
        return self


class ProcurementCommitmentState(str, Enum):
    SENT = "SENT"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    FULLY_RECEIVED = "FULLY_RECEIVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class ProcurementCommitmentFinancialSource(_FinancialSourceContract):
    reference: FinancialSourceReference
    purchase_order_id: str
    purchase_order_line_id: str
    purchase_order_number: str
    supplier_party_id: str
    site_id: str
    state: ProcurementCommitmentState
    ordered_quantity: DecimalQuantityPayload
    unit_price: MonetaryRatePayload
    order_date: date | None = None
    expected_delivery_date: date | None = None
    source_requisition_id: str | None = None
    source_requisition_line_id: str | None = None
    task_id: str | None = None

    @field_validator(
        "purchase_order_id",
        "purchase_order_line_id",
        "purchase_order_number",
        "supplier_party_id",
        "site_id",
        mode="before",
    )
    @classmethod
    def _validate_required_text(cls, value: object, info) -> str:
        return _required_text(value, label=info.field_name.replace("_", " ").capitalize())

    @field_validator("source_requisition_id", "source_requisition_line_id", "task_id", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: object) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    @model_validator(mode="after")
    def _validate_commitment_source(self) -> "ProcurementCommitmentFinancialSource":
        reference = self.reference
        if (
            reference.source_module != FinancialSourceModule.INVENTORY_PROCUREMENT
            or reference.source_type != FinancialSourceType.PURCHASE_ORDER_LINE
            or reference.posting_purpose != FinancialPostingPurpose.PURCHASE_COMMITMENT
        ):
            raise ValueError("Procurement commitment source reference is incompatible")
        if reference.source_id != self.purchase_order_id or reference.source_line_id != self.purchase_order_line_id:
            raise ValueError("Purchase order source IDs must match the source reference")
        if Decimal(self.ordered_quantity.value) <= 0:
            raise ValueError("Ordered quantity must be positive")
        if self.ordered_quantity.unit != self.unit_price.per_unit:
            raise ValueError("Purchase order quantity and unit price units must match")
        if Decimal(self.unit_price.amount) < 0:
            raise ValueError("Purchase order unit price cannot be negative")
        return self


class ProcurementReceiptAccrualFinancialSource(_FinancialSourceContract):
    reference: FinancialSourceReference
    receipt_status: Literal["POSTED"] = "POSTED"
    receipt_id: str
    receipt_line_id: str
    receipt_number: str
    purchase_order_id: str
    purchase_order_line_id: str
    supplier_party_id: str
    site_id: str
    posted_at: AwareDatetime
    accepted_quantity: DecimalQuantityPayload
    unit_cost: MonetaryRatePayload
    task_id: str | None = None

    @field_validator(
        "receipt_id",
        "receipt_line_id",
        "receipt_number",
        "purchase_order_id",
        "purchase_order_line_id",
        "supplier_party_id",
        "site_id",
        mode="before",
    )
    @classmethod
    def _validate_required_text(cls, value: object, info) -> str:
        return _required_text(value, label=info.field_name.replace("_", " ").capitalize())

    @field_validator("task_id", mode="before")
    @classmethod
    def _normalize_task_id(cls, value: object) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    @field_validator("posted_at", mode="after")
    @classmethod
    def _normalize_posted_at(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def _validate_receipt_source(self) -> "ProcurementReceiptAccrualFinancialSource":
        reference = self.reference
        if (
            reference.source_module != FinancialSourceModule.INVENTORY_PROCUREMENT
            or reference.source_type != FinancialSourceType.RECEIPT_LINE
            or reference.posting_purpose != FinancialPostingPurpose.RECEIPT_ACCRUAL
        ):
            raise ValueError("Procurement receipt source reference is incompatible")
        if reference.source_id != self.receipt_id or reference.source_line_id != self.receipt_line_id:
            raise ValueError("Receipt source IDs must match the source reference")
        if Decimal(self.accepted_quantity.value) <= 0:
            raise ValueError("Accepted receipt quantity must be positive")
        if self.accepted_quantity.unit != self.unit_cost.per_unit:
            raise ValueError("Receipt quantity and unit cost units must match")
        if Decimal(self.unit_cost.amount) < 0:
            raise ValueError("Receipt unit cost cannot be negative")
        return self


FinancialSourceT = TypeVar("FinancialSourceT", bound=_FinancialSourceContract)


class FinancialSourcePage(_FinancialSourceContract, Generic[FinancialSourceT]):
    items: tuple[FinancialSourceT, ...]
    next_cursor: str | None = None

    @field_validator("next_cursor", mode="before")
    @classmethod
    def _normalize_next_cursor(cls, value: object) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None


class ApprovedTimeFinancialSourceProvider(Protocol):
    def list_approved_time_sources(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        cursor: str | None = None,
        limit: int = 100,
    ) -> FinancialSourcePage[ApprovedTimeFinancialSource]: ...


class ProcurementFinancialSourceProvider(Protocol):
    def list_commitment_sources(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        cursor: str | None = None,
        limit: int = 100,
    ) -> FinancialSourcePage[ProcurementCommitmentFinancialSource]: ...

    def list_receipt_accrual_sources(
        self,
        *,
        tenant_id: str,
        organization_id: str,
        project_id: str,
        cursor: str | None = None,
        limit: int = 100,
    ) -> FinancialSourcePage[ProcurementReceiptAccrualFinancialSource]: ...


__all__ = [
    "ApprovedTimeFinancialSource",
    "ApprovedTimeFinancialSourceProvider",
    "FinancialPostingPurpose",
    "FinancialSourceModule",
    "FinancialSourcePage",
    "FinancialSourceReference",
    "FinancialSourceType",
    "ProcurementCommitmentFinancialSource",
    "ProcurementCommitmentState",
    "ProcurementFinancialSourceProvider",
    "ProcurementReceiptAccrualFinancialSource",
    "financial_source_content_hash",
]
