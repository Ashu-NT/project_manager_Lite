from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import AwareDatetime, field_validator, model_validator

from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialPostingPurpose,
    FinancialSourceModule,
    FinancialSourceReference,
    FinancialSourceType,
    _FinancialSourceContract,
    _required_text,
)
from src.core.platform.finance.money.serialization import (
    DecimalQuantityPayload,
    MonetaryRatePayload,
)


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


__all__ = [
    "ProcurementCommitmentFinancialSource",
    "ProcurementCommitmentState",
    "ProcurementReceiptAccrualFinancialSource",
]
