from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.modules.inventory_procurement.domain import (
    PurchaseOrderLineStatus,
    PurchaseOrderStatus,
    PurchaseRequisitionLineStatus,
    PurchaseRequisitionStatus,
    ReceiptStatus,
    StockReservationStatus,
    StockTransactionType,
)
from infra.platform.db.base import Base


class InventoryItemCategoryORM(Base):
    __tablename__ = "inventory_item_categories"
    __table_args__ = (
        UniqueConstraint("organization_id", "category_code", name="ux_inventory_item_categories_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category_type: Mapped[str] = mapped_column(String(32), nullable=False, default="MATERIAL", server_default="MATERIAL")
    is_equipment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    supports_project_usage: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    supports_maintenance_usage: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class StockItemORM(Base):
    __tablename__ = "inventory_stock_items"
    __table_args__ = (
        UniqueConstraint("organization_id", "item_code", name="ux_inventory_stock_items_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    item_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", server_default="DRAFT")
    stock_uom: Mapped[str] = mapped_column(String(32), nullable=False)
    order_uom: Mapped[str] = mapped_column(String(32), nullable=False)
    issue_uom: Mapped[str] = mapped_column(String(32), nullable=False)
    order_uom_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1.0")
    issue_uom_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=1.0, server_default="1.0")
    category_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    commodity_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_stocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    is_purchase_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    default_reorder_policy: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    min_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    max_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    reorder_point: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    reorder_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_lot_tracked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_serial_tracked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    shelf_life_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preferred_party_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("parties.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class StoreroomORM(Base):
    __tablename__ = "inventory_storerooms"
    __table_args__ = (
        UniqueConstraint("organization_id", "storeroom_code", name="ux_inventory_storerooms_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    storeroom_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    site_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("sites.id"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", server_default="DRAFT")
    storeroom_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    is_internal_supplier: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    allows_issue: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    allows_transfer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    allows_receiving: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    requires_reservation_for_issue: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    requires_supplier_reference_for_receipt: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    default_currency_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    manager_party_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("parties.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class StockBalanceORM(Base):
    __tablename__ = "inventory_stock_balances"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "stock_item_id",
            "storeroom_id",
            name="ux_inventory_stock_balances_position",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    stock_item_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_stock_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    storeroom_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_storerooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    uom: Mapped[str] = mapped_column(String(32), nullable=False)
    on_hand_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    reserved_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    available_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    on_order_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    committed_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    average_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    last_receipt_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_issue_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reorder_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class StockTransactionORM(Base):
    __tablename__ = "inventory_stock_transactions"
    __table_args__ = (
        UniqueConstraint("organization_id", "transaction_number", name="ux_inventory_stock_transactions_number"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    transaction_number: Mapped[str] = mapped_column(String(64), nullable=False)
    stock_item_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_stock_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    storeroom_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_storerooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    transaction_type: Mapped[StockTransactionType] = mapped_column(SAEnum(StockTransactionType), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    uom: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    transaction_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    reference_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    reference_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    performed_by_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    performed_by_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    resulting_on_hand_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    resulting_available_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class StockReservationORM(Base):
    __tablename__ = "inventory_stock_reservations"
    __table_args__ = (
        UniqueConstraint("organization_id", "reservation_number", name="ux_inventory_stock_reservations_number"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    reservation_number: Mapped[str] = mapped_column(String(64), nullable=False)
    stock_item_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_stock_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    storeroom_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_storerooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    reserved_qty: Mapped[float] = mapped_column(Float, nullable=False)
    issued_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    remaining_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    uom: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[StockReservationStatus] = mapped_column(
        SAEnum(StockReservationStatus),
        nullable=False,
        default=StockReservationStatus.ACTIVE,
        server_default=StockReservationStatus.ACTIVE.value,
    )
    need_by_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source_reference_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_reference_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    requested_by_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_by_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class PurchaseRequisitionORM(Base):
    __tablename__ = "inventory_purchase_requisitions"
    __table_args__ = (
        UniqueConstraint("organization_id", "requisition_number", name="ux_inventory_requisitions_number"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    requisition_number: Mapped[str] = mapped_column(String(64), nullable=False)
    requesting_site_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("sites.id"),
        nullable=False,
    )
    requesting_storeroom_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_storerooms.id"),
        nullable=False,
    )
    requester_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    requester_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    status: Mapped[PurchaseRequisitionStatus] = mapped_column(
        SAEnum(PurchaseRequisitionStatus),
        nullable=False,
        default=PurchaseRequisitionStatus.DRAFT,
        server_default=PurchaseRequisitionStatus.DRAFT.value,
    )
    purpose: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    needed_by_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    approval_request_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("approval_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_reference_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_reference_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class PurchaseRequisitionLineORM(Base):
    __tablename__ = "inventory_purchase_requisition_lines"
    __table_args__ = (
        UniqueConstraint(
            "purchase_requisition_id",
            "line_number",
            name="ux_inventory_requisition_lines_number",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    purchase_requisition_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_purchase_requisitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_item_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_stock_items.id"),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantity_requested: Mapped[float] = mapped_column(Float, nullable=False)
    uom: Mapped[str] = mapped_column(String(32), nullable=False)
    needed_by_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    estimated_unit_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    quantity_sourced: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    suggested_supplier_party_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("parties.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[PurchaseRequisitionLineStatus] = mapped_column(
        SAEnum(PurchaseRequisitionLineStatus),
        nullable=False,
        default=PurchaseRequisitionLineStatus.DRAFT,
        server_default=PurchaseRequisitionLineStatus.DRAFT.value,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PurchaseOrderORM(Base):
    __tablename__ = "inventory_purchase_orders"
    __table_args__ = (
        UniqueConstraint("organization_id", "po_number", name="ux_inventory_purchase_orders_number"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    po_number: Mapped[str] = mapped_column(String(64), nullable=False)
    site_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("sites.id"),
        nullable=False,
    )
    supplier_party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id"),
        nullable=False,
    )
    status: Mapped[PurchaseOrderStatus] = mapped_column(
        SAEnum(PurchaseOrderStatus),
        nullable=False,
        default=PurchaseOrderStatus.DRAFT,
        server_default=PurchaseOrderStatus.DRAFT.value,
    )
    order_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expected_delivery_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    currency_code: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    approval_request_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("approval_requests.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_requisition_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("inventory_purchase_requisitions.id", ondelete="SET NULL"),
        nullable=True,
    )
    supplier_reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class PurchaseOrderLineORM(Base):
    __tablename__ = "inventory_purchase_order_lines"
    __table_args__ = (
        UniqueConstraint("purchase_order_id", "line_number", name="ux_inventory_purchase_order_lines_number"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    purchase_order_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_item_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_stock_items.id"),
        nullable=False,
    )
    destination_storeroom_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_storerooms.id"),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantity_ordered: Mapped[float] = mapped_column(Float, nullable=False)
    quantity_received: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    quantity_rejected: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    uom: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    expected_delivery_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source_requisition_line_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("inventory_purchase_requisition_lines.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[PurchaseOrderLineStatus] = mapped_column(
        SAEnum(PurchaseOrderLineStatus),
        nullable=False,
        default=PurchaseOrderLineStatus.DRAFT,
        server_default=PurchaseOrderLineStatus.DRAFT.value,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ReceiptHeaderORM(Base):
    __tablename__ = "inventory_receipt_headers"
    __table_args__ = (
        UniqueConstraint("organization_id", "receipt_number", name="ux_inventory_receipt_headers_number"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    receipt_number: Mapped[str] = mapped_column(String(64), nullable=False)
    purchase_order_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    received_site_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("sites.id"),
        nullable=False,
    )
    supplier_party_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("parties.id"),
        nullable=False,
    )
    status: Mapped[ReceiptStatus] = mapped_column(
        SAEnum(ReceiptStatus),
        nullable=False,
        default=ReceiptStatus.POSTED,
        server_default=ReceiptStatus.POSTED.value,
    )
    receipt_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    supplier_delivery_reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    received_by_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    received_by_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class ReceiptLineORM(Base):
    __tablename__ = "inventory_receipt_lines"
    __table_args__ = (
        UniqueConstraint("receipt_header_id", "line_number", name="ux_inventory_receipt_lines_number"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    receipt_header_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_receipt_headers.id", ondelete="CASCADE"),
        nullable=False,
    )
    purchase_order_line_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_purchase_order_lines.id", ondelete="CASCADE"),
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_item_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_stock_items.id"),
        nullable=False,
    )
    storeroom_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_storerooms.id"),
        nullable=False,
    )
    quantity_accepted: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    quantity_rejected: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    uom: Mapped[str] = mapped_column(String(32), nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    lot_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


Index("idx_inventory_item_categories_org", InventoryItemCategoryORM.organization_id)
Index("idx_inventory_item_categories_active", InventoryItemCategoryORM.is_active)
Index("idx_inventory_stock_items_org", StockItemORM.organization_id)
Index("idx_inventory_stock_items_active", StockItemORM.is_active)
Index("idx_inventory_storerooms_org", StoreroomORM.organization_id)
Index("idx_inventory_storerooms_site", StoreroomORM.site_id)
Index("idx_inventory_storerooms_active", StoreroomORM.is_active)
Index("idx_inventory_stock_balances_org", StockBalanceORM.organization_id)
Index("idx_inventory_stock_balances_item", StockBalanceORM.stock_item_id)
Index("idx_inventory_stock_balances_storeroom", StockBalanceORM.storeroom_id)
Index("idx_inventory_stock_transactions_org", StockTransactionORM.organization_id)
Index("idx_inventory_stock_transactions_item", StockTransactionORM.stock_item_id)
Index("idx_inventory_stock_transactions_storeroom", StockTransactionORM.storeroom_id)
Index("idx_inventory_stock_transactions_at", StockTransactionORM.transaction_at)
Index("idx_inventory_stock_reservations_org", StockReservationORM.organization_id)
Index("idx_inventory_stock_reservations_item", StockReservationORM.stock_item_id)
Index("idx_inventory_stock_reservations_storeroom", StockReservationORM.storeroom_id)
Index("idx_inventory_stock_reservations_status", StockReservationORM.status)
Index("idx_inventory_requisitions_org", PurchaseRequisitionORM.organization_id)
Index("idx_inventory_requisitions_status", PurchaseRequisitionORM.status)
Index("idx_inventory_requisitions_site", PurchaseRequisitionORM.requesting_site_id)
Index("idx_inventory_requisitions_storeroom", PurchaseRequisitionORM.requesting_storeroom_id)
Index("idx_inventory_requisition_lines_requisition", PurchaseRequisitionLineORM.purchase_requisition_id)
Index("idx_inventory_requisition_lines_item", PurchaseRequisitionLineORM.stock_item_id)
Index("idx_inventory_purchase_orders_org", PurchaseOrderORM.organization_id)
Index("idx_inventory_purchase_orders_status", PurchaseOrderORM.status)
Index("idx_inventory_purchase_orders_site", PurchaseOrderORM.site_id)
Index("idx_inventory_purchase_orders_supplier", PurchaseOrderORM.supplier_party_id)
Index("idx_inventory_purchase_order_lines_order", PurchaseOrderLineORM.purchase_order_id)
Index("idx_inventory_purchase_order_lines_item", PurchaseOrderLineORM.stock_item_id)
Index("idx_inventory_purchase_order_lines_storeroom", PurchaseOrderLineORM.destination_storeroom_id)
Index("idx_inventory_purchase_order_lines_req_line", PurchaseOrderLineORM.source_requisition_line_id)
Index("idx_inventory_receipt_headers_org", ReceiptHeaderORM.organization_id)
Index("idx_inventory_receipt_headers_order", ReceiptHeaderORM.purchase_order_id)
Index("idx_inventory_receipt_headers_date", ReceiptHeaderORM.receipt_date)
Index("idx_inventory_receipt_lines_receipt", ReceiptLineORM.receipt_header_id)
Index("idx_inventory_receipt_lines_po_line", ReceiptLineORM.purchase_order_line_id)


__all__ = [
    "InventoryItemCategoryORM",
    "PurchaseOrderLineORM",
    "PurchaseOrderORM",
    "PurchaseRequisitionLineORM",
    "PurchaseRequisitionORM",
    "ReceiptHeaderORM",
    "ReceiptLineORM",
    "StockBalanceORM",
    "StockItemORM",
    "StockReservationORM",
    "StockTransactionORM",
    "StoreroomORM",
]
