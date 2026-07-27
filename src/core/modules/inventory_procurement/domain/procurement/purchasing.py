from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum

from src.core.platform.common.ids import generate_id
from src.core.platform.common.pydantic import validated_dataclass
from src.core.modules.inventory_procurement.domain._validation import (
    normalize_currency_code,
    normalize_enum,
    normalize_inventory_code,
    normalize_nonnegative_quantity,
    normalize_optional_date,
    normalize_optional_datetime,
    normalize_optional_identifier,
    normalize_optional_text,
    normalize_positive_int,
    normalize_positive_quantity,
    normalize_procurement_priority,
    normalize_required_text,
    normalize_source_reference_type,
    normalize_uom,
)
from src.core.platform.common.exceptions import ValidationError
from pydantic import field_validator, model_validator


class PurchaseRequisitionStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PARTIALLY_SOURCED = "PARTIALLY_SOURCED"
    FULLY_SOURCED = "FULLY_SOURCED"
    CANCELLED = "CANCELLED"
    CLOSED = "CLOSED"


class PurchaseRequisitionLineStatus(str, Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    PARTIALLY_SOURCED = "PARTIALLY_SOURCED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    FULLY_SOURCED = "FULLY_SOURCED"


class PurchaseOrderStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SENT = "SENT"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    FULLY_RECEIVED = "FULLY_RECEIVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PurchaseOrderLineStatus(str, Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    FULLY_RECEIVED = "FULLY_RECEIVED"
    CANCELLED = "CANCELLED"


class ReceiptStatus(str, Enum):
    POSTED = "POSTED"


@validated_dataclass
class PurchaseRequisition:
    id: str
    organization_id: str
    requisition_number: str
    requesting_site_id: str
    requesting_storeroom_id: str
    requester_user_id: str | None = None
    requester_username: str = ""
    status: PurchaseRequisitionStatus = PurchaseRequisitionStatus.DRAFT
    purpose: str = ""
    needed_by_date: date | None = None
    priority: str = ""
    approval_request_id: str | None = None
    source_reference_type: str = ""
    source_reference_id: str = ""
    source_module: str = ""
    source_entity_type: str = ""
    source_code_snapshot: str = ""
    source_title_snapshot: str = ""
    source_status_snapshot: str = ""
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    cancelled_at: datetime | None = None
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @field_validator(
        "id",
        "organization_id",
        "requesting_site_id",
        "requesting_storeroom_id",
        mode="before",
    )
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Purchase requisition ID is required.",
                "INVENTORY_REQUISITION_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "INVENTORY_REQUISITION_ORGANIZATION_REQUIRED",
            ),
            "requesting_site_id": ("Site ID is required.", "INVENTORY_SITE_REQUIRED"),
            "requesting_storeroom_id": (
                "Storeroom ID is required.",
                "INVENTORY_STOREROOM_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("requisition_number", mode="before")
    @classmethod
    def _validate_requisition_number(cls, value: object) -> str:
        return normalize_inventory_code(value, label="Requisition number")

    @field_validator("requester_user_id", "approval_request_id", mode="before")
    @classmethod
    def _normalize_optional_identifiers(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> PurchaseRequisitionStatus:
        return normalize_enum(
            value,
            enum_type=PurchaseRequisitionStatus,
            default=PurchaseRequisitionStatus.DRAFT,
            message="Purchase requisition status is invalid.",
            code="INVENTORY_REQUISITION_STATUS_INVALID",
        )

    @field_validator("priority", mode="before")
    @classmethod
    def _validate_priority(cls, value: object) -> str:
        return normalize_procurement_priority(value)

    @field_validator("needed_by_date", mode="before")
    @classmethod
    def _validate_needed_by_date(cls, value: object) -> date | None:
        return normalize_optional_date(value, label="Needed-by date")

    @field_validator("source_reference_type", mode="before")
    @classmethod
    def _validate_source_reference_type(cls, value: object) -> str:
        return normalize_source_reference_type(str(value or ""))

    @field_validator("source_reference_id", mode="before")
    @classmethod
    def _normalize_optional_source_reference_id(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator(
        "requester_username",
        "purpose",
        "source_module",
        "source_entity_type",
        "source_code_snapshot",
        "source_title_snapshot",
        "source_status_snapshot",
        "notes",
        mode="before",
    )
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator(
        "submitted_at",
        "approved_at",
        "cancelled_at",
        "created_at",
        "updated_at",
        mode="before",
    )
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Purchase requisition {info.field_name.replace('_', ' ')} is invalid.",
            code=f"INVENTORY_REQUISITION_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Purchase requisition version must be positive.",
            code="INVENTORY_REQUISITION_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "PurchaseRequisition":
        if bool(self.source_reference_type) != bool(self.source_reference_id):
            raise ValidationError(
                "Source reference type and ID must be provided together.",
                code="INVENTORY_REQUISITION_SOURCE_REQUIRED",
            )
        if self.approved_at is not None and self.cancelled_at is not None:
            raise ValidationError(
                "Purchase requisition cannot be both approved and cancelled.",
                code="INVENTORY_REQUISITION_CLOSED_STATE_INVALID",
            )
        if (
            self.created_at is not None
            and self.updated_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="INVENTORY_REQUISITION_UPDATED_RANGE_INVALID",
            )
        for field_name, value, code in (
            (
                "submitted",
                self.submitted_at,
                "INVENTORY_REQUISITION_SUBMITTED_RANGE_INVALID",
            ),
            (
                "approved",
                self.approved_at,
                "INVENTORY_REQUISITION_APPROVED_RANGE_INVALID",
            ),
            (
                "cancelled",
                self.cancelled_at,
                "INVENTORY_REQUISITION_CANCELLED_RANGE_INVALID",
            ),
        ):
            if self.created_at is not None and value is not None and value < self.created_at:
                raise ValidationError(
                    f"{field_name.capitalize()} timestamp cannot be earlier than created timestamp.",
                    code=code,
                )
            if self.updated_at is not None and value is not None and value > self.updated_at:
                raise ValidationError(
                    f"{field_name.capitalize()} timestamp cannot be later than updated timestamp.",
                    code=code,
                )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        requisition_number: str,
        requesting_site_id: str,
        requesting_storeroom_id: str,
        requester_user_id: str | None = None,
        requester_username: str = "",
        status: PurchaseRequisitionStatus = PurchaseRequisitionStatus.DRAFT,
        purpose: str = "",
        needed_by_date: date | None = None,
        priority: str = "",
        approval_request_id: str | None = None,
        source_reference_type: str = "",
        source_reference_id: str = "",
        source_module: str = "",
        source_entity_type: str = "",
        source_code_snapshot: str = "",
        source_title_snapshot: str = "",
        source_status_snapshot: str = "",
        submitted_at: datetime | None = None,
        approved_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        notes: str = "",
    ) -> "PurchaseRequisition":
        now = datetime.now(timezone.utc)
        return PurchaseRequisition(
            id=generate_id(),
            organization_id=organization_id,
            requisition_number=requisition_number,
            requesting_site_id=requesting_site_id,
            requesting_storeroom_id=requesting_storeroom_id,
            requester_user_id=requester_user_id,
            requester_username=requester_username,
            status=status,
            purpose=purpose,
            needed_by_date=needed_by_date,
            priority=priority,
            approval_request_id=approval_request_id,
            source_reference_type=source_reference_type,
            source_reference_id=source_reference_id,
            source_module=source_module,
            source_entity_type=source_entity_type,
            source_code_snapshot=source_code_snapshot,
            source_title_snapshot=source_title_snapshot,
            source_status_snapshot=source_status_snapshot,
            submitted_at=submitted_at,
            approved_at=approved_at,
            cancelled_at=cancelled_at,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@validated_dataclass
class PurchaseRequisitionLine:
    id: str
    purchase_requisition_id: str
    line_number: int
    stock_item_id: str
    description: str = ""
    quantity_requested: float = 0.0
    uom: str = ""
    needed_by_date: date | None = None
    estimated_unit_cost: float = 0.0
    quantity_sourced: float = 0.0
    suggested_supplier_party_id: str | None = None
    status: PurchaseRequisitionLineStatus = PurchaseRequisitionLineStatus.DRAFT
    notes: str = ""

    @field_validator("id", "purchase_requisition_id", "stock_item_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Purchase requisition line ID is required.",
                "INVENTORY_REQUISITION_LINE_ID_REQUIRED",
            ),
            "purchase_requisition_id": (
                "Purchase requisition ID is required.",
                "INVENTORY_REQUISITION_REQUIRED",
            ),
            "stock_item_id": ("Stock item ID is required.", "INVENTORY_ITEM_REQUIRED"),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("line_number", mode="before")
    @classmethod
    def _validate_line_number(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Purchase requisition line number must be positive.",
            code="INVENTORY_REQUISITION_LINE_NUMBER_INVALID",
        )

    @field_validator("description", "notes", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("quantity_requested", mode="before")
    @classmethod
    def _validate_quantity_requested(cls, value: object) -> float:
        return normalize_positive_quantity(value, label="Requisition quantity")

    @field_validator("uom", mode="before")
    @classmethod
    def _validate_uom(cls, value: object) -> str:
        return normalize_uom(value, label="Requisition line UOM")

    @field_validator("needed_by_date", mode="before")
    @classmethod
    def _validate_needed_by_date(cls, value: object) -> date | None:
        return normalize_optional_date(value, label="Needed-by date")

    @field_validator("estimated_unit_cost", "quantity_sourced", mode="before")
    @classmethod
    def _validate_nonnegative_amounts(cls, value: object, info) -> float:
        labels = {
            "estimated_unit_cost": "Estimated unit cost",
            "quantity_sourced": "Sourced quantity",
        }
        return normalize_nonnegative_quantity(value, label=labels[info.field_name])

    @field_validator("suggested_supplier_party_id", mode="before")
    @classmethod
    def _normalize_supplier_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> PurchaseRequisitionLineStatus:
        return normalize_enum(
            value,
            enum_type=PurchaseRequisitionLineStatus,
            default=PurchaseRequisitionLineStatus.DRAFT,
            message="Purchase requisition line status is invalid.",
            code="INVENTORY_REQUISITION_LINE_STATUS_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "PurchaseRequisitionLine":
        requested = float(self.quantity_requested or 0.0)
        sourced = float(self.quantity_sourced or 0.0)
        if sourced > requested + 1e-9:
            raise ValidationError(
                "Sourced quantity cannot exceed requested quantity.",
                code="INVENTORY_REQUISITION_LINE_QTY_INVALID",
            )
        if self.status in {
            PurchaseRequisitionLineStatus.DRAFT,
            PurchaseRequisitionLineStatus.OPEN,
        } and sourced > 1e-9:
            raise ValidationError(
                "Draft or open requisition lines cannot already be sourced.",
                code="INVENTORY_REQUISITION_LINE_QTY_INVALID",
            )
        if self.status == PurchaseRequisitionLineStatus.PARTIALLY_SOURCED and (
            sourced <= 0 or sourced >= requested
        ):
            raise ValidationError(
                "Partially sourced requisition line quantities are invalid.",
                code="INVENTORY_REQUISITION_LINE_QTY_INVALID",
            )
        if self.status == PurchaseRequisitionLineStatus.FULLY_SOURCED and abs(sourced - requested) > 1e-9:
            raise ValidationError(
                "Fully sourced requisition line must have all requested quantity sourced.",
                code="INVENTORY_REQUISITION_LINE_QTY_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        purchase_requisition_id: str,
        line_number: int,
        stock_item_id: str,
        description: str = "",
        quantity_requested: float,
        uom: str,
        needed_by_date: date | None = None,
        estimated_unit_cost: float = 0.0,
        quantity_sourced: float = 0.0,
        suggested_supplier_party_id: str | None = None,
        status: PurchaseRequisitionLineStatus = PurchaseRequisitionLineStatus.DRAFT,
        notes: str = "",
    ) -> "PurchaseRequisitionLine":
        return PurchaseRequisitionLine(
            id=generate_id(),
            purchase_requisition_id=purchase_requisition_id,
            line_number=line_number,
            stock_item_id=stock_item_id,
            description=description,
            quantity_requested=quantity_requested,
            uom=uom,
            needed_by_date=needed_by_date,
            estimated_unit_cost=estimated_unit_cost,
            quantity_sourced=quantity_sourced,
            suggested_supplier_party_id=suggested_supplier_party_id,
            status=status,
            notes=notes,
        )


@validated_dataclass
class PurchaseOrder:
    id: str
    organization_id: str
    po_number: str
    site_id: str
    supplier_party_id: str
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    order_date: date | None = None
    expected_delivery_date: date | None = None
    currency_code: str = ""
    approval_request_id: str | None = None
    source_requisition_id: str | None = None
    supplier_reference: str = ""
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    sent_at: datetime | None = None
    closed_at: datetime | None = None
    cancelled_at: datetime | None = None
    notes: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @field_validator("id", "organization_id", "site_id", "supplier_party_id", mode="before")
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Purchase order ID is required.",
                "INVENTORY_PURCHASE_ORDER_ID_REQUIRED",
            ),
            "organization_id": (
                "Organization ID is required.",
                "INVENTORY_PURCHASE_ORDER_ORGANIZATION_REQUIRED",
            ),
            "site_id": ("Site ID is required.", "INVENTORY_SITE_REQUIRED"),
            "supplier_party_id": (
                "Supplier party ID is required.",
                "INVENTORY_SUPPLIER_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("po_number", mode="before")
    @classmethod
    def _validate_po_number(cls, value: object) -> str:
        return normalize_inventory_code(value, label="Purchase order number")

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> PurchaseOrderStatus:
        return normalize_enum(
            value,
            enum_type=PurchaseOrderStatus,
            default=PurchaseOrderStatus.DRAFT,
            message="Purchase order status is invalid.",
            code="INVENTORY_PURCHASE_ORDER_STATUS_INVALID",
        )

    @field_validator("order_date", "expected_delivery_date", mode="before")
    @classmethod
    def _validate_dates(cls, value: object, info) -> date | None:
        labels = {
            "order_date": "Order date",
            "expected_delivery_date": "Expected delivery date",
        }
        return normalize_optional_date(value, label=labels[info.field_name])

    @field_validator("currency_code", mode="before")
    @classmethod
    def _validate_currency_code(cls, value: object) -> str:
        return normalize_currency_code(value)

    @field_validator("approval_request_id", "source_requisition_id", mode="before")
    @classmethod
    def _normalize_optional_ids(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("supplier_reference", "notes", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator(
        "submitted_at",
        "approved_at",
        "sent_at",
        "closed_at",
        "cancelled_at",
        "created_at",
        "updated_at",
        mode="before",
    )
    @classmethod
    def _validate_timestamps(cls, value: object, info) -> datetime | None:
        return normalize_optional_datetime(
            value,
            message=f"Purchase order {info.field_name.replace('_', ' ')} is invalid.",
            code=f"INVENTORY_PURCHASE_ORDER_{info.field_name.upper()}_INVALID",
        )

    @field_validator("version", mode="before")
    @classmethod
    def _validate_version(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Purchase order version must be positive.",
            code="INVENTORY_PURCHASE_ORDER_VERSION_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "PurchaseOrder":
        if (
            self.order_date is not None
            and self.expected_delivery_date is not None
            and self.expected_delivery_date < self.order_date
        ):
            raise ValidationError(
                "Expected delivery date cannot be earlier than order date.",
                code="INVENTORY_PURCHASE_ORDER_DELIVERY_RANGE_INVALID",
            )
        if self.closed_at is not None and self.cancelled_at is not None:
            raise ValidationError(
                "Purchase order cannot be both closed and cancelled.",
                code="INVENTORY_PURCHASE_ORDER_CLOSED_STATE_INVALID",
            )
        if (
            self.created_at is not None
            and self.updated_at is not None
            and self.updated_at < self.created_at
        ):
            raise ValidationError(
                "Updated timestamp cannot be earlier than created timestamp.",
                code="INVENTORY_PURCHASE_ORDER_UPDATED_RANGE_INVALID",
            )
        for field_name, value, code in (
            ("submitted", self.submitted_at, "INVENTORY_PURCHASE_ORDER_SUBMITTED_RANGE_INVALID"),
            ("approved", self.approved_at, "INVENTORY_PURCHASE_ORDER_APPROVED_RANGE_INVALID"),
            ("sent", self.sent_at, "INVENTORY_PURCHASE_ORDER_SENT_RANGE_INVALID"),
            ("closed", self.closed_at, "INVENTORY_PURCHASE_ORDER_CLOSED_RANGE_INVALID"),
            ("cancelled", self.cancelled_at, "INVENTORY_PURCHASE_ORDER_CANCELLED_RANGE_INVALID"),
        ):
            if self.created_at is not None and value is not None and value < self.created_at:
                raise ValidationError(
                    f"{field_name.capitalize()} timestamp cannot be earlier than created timestamp.",
                    code=code,
                )
            if self.updated_at is not None and value is not None and value > self.updated_at:
                raise ValidationError(
                    f"{field_name.capitalize()} timestamp cannot be later than updated timestamp.",
                    code=code,
                )
        return self

    @staticmethod
    def create(
        *,
        organization_id: str,
        po_number: str,
        site_id: str,
        supplier_party_id: str,
        status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT,
        order_date: date | None = None,
        expected_delivery_date: date | None = None,
        currency_code: str = "",
        approval_request_id: str | None = None,
        source_requisition_id: str | None = None,
        supplier_reference: str = "",
        submitted_at: datetime | None = None,
        approved_at: datetime | None = None,
        sent_at: datetime | None = None,
        closed_at: datetime | None = None,
        cancelled_at: datetime | None = None,
        notes: str = "",
    ) -> "PurchaseOrder":
        now = datetime.now(timezone.utc)
        return PurchaseOrder(
            id=generate_id(),
            organization_id=organization_id,
            po_number=po_number,
            site_id=site_id,
            supplier_party_id=supplier_party_id,
            status=status,
            order_date=order_date,
            expected_delivery_date=expected_delivery_date,
            currency_code=currency_code,
            approval_request_id=approval_request_id,
            source_requisition_id=source_requisition_id,
            supplier_reference=supplier_reference,
            submitted_at=submitted_at,
            approved_at=approved_at,
            sent_at=sent_at,
            closed_at=closed_at,
            cancelled_at=cancelled_at,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )


@validated_dataclass
class PurchaseOrderLine:
    id: str
    purchase_order_id: str
    line_number: int
    stock_item_id: str
    destination_storeroom_id: str
    description: str = ""
    quantity_ordered: float = 0.0
    quantity_received: float = 0.0
    quantity_rejected: float = 0.0
    uom: str = ""
    unit_price: float = 0.0
    expected_delivery_date: date | None = None
    source_requisition_line_id: str | None = None
    status: PurchaseOrderLineStatus = PurchaseOrderLineStatus.DRAFT
    notes: str = ""

    @field_validator(
        "id",
        "purchase_order_id",
        "stock_item_id",
        "destination_storeroom_id",
        mode="before",
    )
    @classmethod
    def _validate_required_ids(cls, value: object, info) -> str:
        messages = {
            "id": (
                "Purchase order line ID is required.",
                "INVENTORY_PURCHASE_ORDER_LINE_ID_REQUIRED",
            ),
            "purchase_order_id": (
                "Purchase order ID is required.",
                "INVENTORY_PURCHASE_ORDER_REQUIRED",
            ),
            "stock_item_id": ("Stock item ID is required.", "INVENTORY_ITEM_REQUIRED"),
            "destination_storeroom_id": (
                "Destination storeroom ID is required.",
                "INVENTORY_STOREROOM_REQUIRED",
            ),
        }
        message, code = messages[info.field_name]
        return normalize_required_text(value, message=message, code=code)

    @field_validator("line_number", mode="before")
    @classmethod
    def _validate_line_number(cls, value: object) -> int:
        return normalize_positive_int(
            value,
            message="Purchase order line number must be positive.",
            code="INVENTORY_PURCHASE_ORDER_LINE_NUMBER_INVALID",
        )

    @field_validator("description", "notes", mode="before")
    @classmethod
    def _normalize_text_fields(cls, value: object) -> str:
        return normalize_optional_text(value)

    @field_validator("quantity_ordered", mode="before")
    @classmethod
    def _validate_quantity_ordered(cls, value: object) -> float:
        return normalize_positive_quantity(value, label="Purchase-order quantity")

    @field_validator("quantity_received", "quantity_rejected", "unit_price", mode="before")
    @classmethod
    def _validate_nonnegative_amounts(cls, value: object, info) -> float:
        labels = {
            "quantity_received": "Received quantity",
            "quantity_rejected": "Rejected quantity",
            "unit_price": "Unit price",
        }
        return normalize_nonnegative_quantity(value, label=labels[info.field_name])

    @field_validator("uom", mode="before")
    @classmethod
    def _validate_uom(cls, value: object) -> str:
        return normalize_uom(value, label="Purchase-order line UOM")

    @field_validator("expected_delivery_date", mode="before")
    @classmethod
    def _validate_expected_delivery_date(cls, value: object) -> date | None:
        return normalize_optional_date(value, label="Expected delivery date")

    @field_validator("source_requisition_line_id", mode="before")
    @classmethod
    def _normalize_optional_source_line_id(cls, value: object) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, value: object) -> PurchaseOrderLineStatus:
        return normalize_enum(
            value,
            enum_type=PurchaseOrderLineStatus,
            default=PurchaseOrderLineStatus.DRAFT,
            message="Purchase order line status is invalid.",
            code="INVENTORY_PURCHASE_ORDER_LINE_STATUS_INVALID",
        )

    @model_validator(mode="after")
    def _validate_ranges(self) -> "PurchaseOrderLine":
        ordered = float(self.quantity_ordered or 0.0)
        processed = float(self.quantity_received or 0.0) + float(self.quantity_rejected or 0.0)
        if processed > ordered + 1e-9:
            raise ValidationError(
                "Processed quantity cannot exceed ordered quantity.",
                code="INVENTORY_PURCHASE_ORDER_LINE_QTY_INVALID",
            )
        if self.status in {
            PurchaseOrderLineStatus.DRAFT,
            PurchaseOrderLineStatus.OPEN,
        } and processed > 1e-9:
            raise ValidationError(
                "Draft or open purchase order lines cannot already be processed.",
                code="INVENTORY_PURCHASE_ORDER_LINE_QTY_INVALID",
            )
        if self.status == PurchaseOrderLineStatus.PARTIALLY_RECEIVED and (
            processed <= 0 or processed >= ordered
        ):
            raise ValidationError(
                "Partially received purchase order line quantities are invalid.",
                code="INVENTORY_PURCHASE_ORDER_LINE_QTY_INVALID",
            )
        if self.status == PurchaseOrderLineStatus.FULLY_RECEIVED and abs(processed - ordered) > 1e-9:
            raise ValidationError(
                "Fully received purchase order line must be fully processed.",
                code="INVENTORY_PURCHASE_ORDER_LINE_QTY_INVALID",
            )
        return self

    @staticmethod
    def create(
        *,
        purchase_order_id: str,
        line_number: int,
        stock_item_id: str,
        destination_storeroom_id: str,
        quantity_ordered: float,
        uom: str,
        description: str = "",
        quantity_received: float = 0.0,
        quantity_rejected: float = 0.0,
        unit_price: float = 0.0,
        expected_delivery_date: date | None = None,
        source_requisition_line_id: str | None = None,
        status: PurchaseOrderLineStatus = PurchaseOrderLineStatus.DRAFT,
        notes: str = "",
    ) -> "PurchaseOrderLine":
        return PurchaseOrderLine(
            id=generate_id(),
            purchase_order_id=purchase_order_id,
            line_number=line_number,
            stock_item_id=stock_item_id,
            destination_storeroom_id=destination_storeroom_id,
            description=description,
            quantity_ordered=quantity_ordered,
            quantity_received=quantity_received,
            quantity_rejected=quantity_rejected,
            uom=uom,
            unit_price=unit_price,
            expected_delivery_date=expected_delivery_date,
            source_requisition_line_id=source_requisition_line_id,
            status=status,
            notes=notes,
        )


@dataclass
class ReceiptHeader:
    id: str
    organization_id: str
    receipt_number: str
    purchase_order_id: str
    received_site_id: str
    supplier_party_id: str
    status: ReceiptStatus = ReceiptStatus.POSTED
    receipt_date: datetime | None = None
    supplier_delivery_reference: str = ""
    received_by_user_id: str | None = None
    received_by_username: str = ""
    notes: str = ""
    created_at: datetime | None = None

    @staticmethod
    def create(
        *,
        organization_id: str,
        receipt_number: str,
        purchase_order_id: str,
        received_site_id: str,
        supplier_party_id: str,
        status: ReceiptStatus = ReceiptStatus.POSTED,
        receipt_date: datetime | None = None,
        supplier_delivery_reference: str = "",
        received_by_user_id: str | None = None,
        received_by_username: str = "",
        notes: str = "",
    ) -> "ReceiptHeader":
        now = datetime.now(timezone.utc)
        effective_receipt_date = receipt_date or now
        return ReceiptHeader(
            id=generate_id(),
            organization_id=organization_id,
            receipt_number=receipt_number,
            purchase_order_id=purchase_order_id,
            received_site_id=received_site_id,
            supplier_party_id=supplier_party_id,
            status=status,
            receipt_date=effective_receipt_date,
            supplier_delivery_reference=supplier_delivery_reference,
            received_by_user_id=received_by_user_id,
            received_by_username=received_by_username,
            notes=notes,
            created_at=now,
        )


@dataclass
class ReceiptLine:
    id: str
    receipt_header_id: str
    purchase_order_line_id: str
    line_number: int
    stock_item_id: str
    storeroom_id: str
    quantity_accepted: float = 0.0
    quantity_rejected: float = 0.0
    uom: str = ""
    unit_cost: float = 0.0
    lot_number: str = ""
    serial_number: str = ""
    expiry_date: date | None = None
    notes: str = ""

    @staticmethod
    def create(
        *,
        receipt_header_id: str,
        purchase_order_line_id: str,
        line_number: int,
        stock_item_id: str,
        storeroom_id: str,
        quantity_accepted: float,
        quantity_rejected: float = 0.0,
        uom: str,
        unit_cost: float = 0.0,
        lot_number: str = "",
        serial_number: str = "",
        expiry_date: date | None = None,
        notes: str = "",
    ) -> "ReceiptLine":
        return ReceiptLine(
            id=generate_id(),
            receipt_header_id=receipt_header_id,
            purchase_order_line_id=purchase_order_line_id,
            line_number=line_number,
            stock_item_id=stock_item_id,
            storeroom_id=storeroom_id,
            quantity_accepted=quantity_accepted,
            quantity_rejected=quantity_rejected,
            uom=uom,
            unit_cost=unit_cost,
            lot_number=lot_number,
            serial_number=serial_number,
            expiry_date=expiry_date,
            notes=notes,
        )


__all__ = [
    "PurchaseOrder",
    "PurchaseOrderLine",
    "PurchaseOrderLineStatus",
    "PurchaseOrderStatus",
    "PurchaseRequisition",
    "PurchaseRequisitionLine",
    "PurchaseRequisitionLineStatus",
    "PurchaseRequisitionStatus",
    "ReceiptHeader",
    "ReceiptLine",
    "ReceiptStatus",
]
