from __future__ import annotations

from datetime import date, datetime, timezone

from pydantic import AwareDatetime, BaseModel, ConfigDict, field_validator, model_validator

from src.core.platform.finance import DecimalQuantityPayload, MonetaryRatePayload


PROCUREMENT_COMMITMENT_EVENT_TYPE = (
    "inventory_procurement.purchase_order_line.financial_state.v1"
)
PROCUREMENT_RECEIPT_ACCRUAL_EVENT_TYPE = (
    "inventory_procurement.receipt_line.posted.v1"
)


class _ProcurementProjectSourcePayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str | None = None
    task_id: str | None = None
    source_module: str = "project_management"

    @field_validator("project_id", "task_id", mode="before")
    @classmethod
    def _optional_id(cls, value: object) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    @field_validator("source_module", mode="before")
    @classmethod
    def _source_module(cls, value: object) -> str:
        normalized = str(value or "").strip().lower()
        if normalized != "project_management":
            raise ValueError("Procurement financial source must originate from Project Management")
        return normalized

    @model_validator(mode="after")
    def _project_reference(self):
        if not self.project_id and not self.task_id:
            raise ValueError("Procurement financial source requires a project or task reference")
        return self


class ProcurementCommitmentEventPayload(_ProcurementProjectSourcePayload):
    purchase_order_id: str
    purchase_order_line_id: str
    purchase_order_number: str
    supplier_party_id: str
    site_id: str
    state: str
    source_revision: int
    source_content_hash: str
    ordered_quantity: DecimalQuantityPayload
    unit_price: MonetaryRatePayload
    order_date: date | None = None
    expected_delivery_date: date | None = None
    source_requisition_id: str | None = None
    source_requisition_line_id: str | None = None

    @field_validator(
        "purchase_order_id",
        "purchase_order_line_id",
        "purchase_order_number",
        "supplier_party_id",
        "site_id",
        mode="before",
    )
    @classmethod
    def _required_id(cls, value: object) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("Procurement commitment event identifiers are required")
        return normalized

    @field_validator("source_requisition_id", "source_requisition_line_id", mode="before")
    @classmethod
    def _optional_source_id(cls, value: object) -> str | None:
        normalized = str(value or "").strip()
        return normalized or None

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, value: object) -> str:
        normalized = str(getattr(value, "value", value) or "").strip().upper()
        allowed = {"SENT", "PARTIALLY_RECEIVED", "FULLY_RECEIVED", "CLOSED", "CANCELLED"}
        if normalized not in allowed:
            raise ValueError("Procurement commitment event state is invalid")
        return normalized

    @field_validator("source_revision", mode="before")
    @classmethod
    def _revision(cls, value: object) -> int:
        revision = int(value)
        if revision < 1:
            raise ValueError("Procurement source revision must be positive")
        return revision

    @field_validator("source_content_hash", mode="before")
    @classmethod
    def _hash(cls, value: object) -> str:
        normalized = str(value or "").strip().lower()
        if len(normalized) != 64 or any(c not in "0123456789abcdef" for c in normalized):
            raise ValueError("Procurement source content hash must be SHA-256")
        return normalized


class ProcurementReceiptAccrualEventPayload(_ProcurementProjectSourcePayload):
    receipt_id: str
    receipt_line_id: str
    receipt_number: str
    purchase_order_id: str
    purchase_order_line_id: str
    supplier_party_id: str
    site_id: str
    source_revision: int = 1
    source_content_hash: str
    posted_at: AwareDatetime
    accepted_quantity: DecimalQuantityPayload
    unit_cost: MonetaryRatePayload

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
    def _required_id(cls, value: object) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            raise ValueError("Procurement receipt event identifiers are required")
        return normalized

    @field_validator("source_revision", mode="before")
    @classmethod
    def _revision(cls, value: object) -> int:
        revision = int(value)
        if revision < 1:
            raise ValueError("Procurement receipt source revision must be positive")
        return revision

    @field_validator("source_content_hash", mode="before")
    @classmethod
    def _hash(cls, value: object) -> str:
        normalized = str(value or "").strip().lower()
        if len(normalized) != 64 or any(c not in "0123456789abcdef" for c in normalized):
            raise ValueError("Procurement receipt content hash must be SHA-256")
        return normalized

    @field_validator("posted_at", mode="after")
    @classmethod
    def _posted_at(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)


__all__ = [
    "PROCUREMENT_COMMITMENT_EVENT_TYPE",
    "PROCUREMENT_RECEIPT_ACCRUAL_EVENT_TYPE",
    "ProcurementCommitmentEventPayload",
    "ProcurementReceiptAccrualEventPayload",
]
