from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.modules.inventory_procurement.domain.inventory.foundation import (
    CycleCountStatus,
    StorageLocationType,
)
from src.core.modules.inventory_procurement.domain.inventory.stock import (
    StockReservationStatus,
    StockTransactionType,
)
from src.infra.persistence.orm.base import Base


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
    source_module: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_entity_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_code_snapshot: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_title_snapshot: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source_status_snapshot: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
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


class StorageLocationORM(Base):
    __tablename__ = "inventory_storage_locations"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "storeroom_id",
            "location_code",
            name="ux_inventory_storage_locations_scope_code",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    storeroom_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("inventory_storerooms.id", ondelete="CASCADE"),
        nullable=False,
    )
    location_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    parent_location_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("inventory_storage_locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    location_type: Mapped[StorageLocationType] = mapped_column(
        SAEnum(StorageLocationType),
        nullable=False,
        default=StorageLocationType.BIN,
        server_default=StorageLocationType.BIN.value,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    is_quarantine: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    allows_issue: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    allows_putaway: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class ReorderPolicyORM(Base):
    __tablename__ = "inventory_reorder_policies"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "stock_item_id",
            "storeroom_id",
            "location_id",
            name="ux_inventory_reorder_policies_scope",
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
    location_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("inventory_storage_locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    policy_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    min_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    max_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    reorder_point: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    reorder_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    economic_order_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    review_period_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    preferred_supplier_party_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("parties.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class CycleCountORM(Base):
    __tablename__ = "inventory_cycle_counts"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "cycle_count_number",
            name="ux_inventory_cycle_counts_number",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    cycle_count_number: Mapped[str] = mapped_column(String(64), nullable=False)
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
    location_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("inventory_storage_locations.id", ondelete="SET NULL"),
        nullable=True,
    )
    scheduled_count_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[CycleCountStatus] = mapped_column(
        SAEnum(CycleCountStatus),
        nullable=False,
        default=CycleCountStatus.PLANNED,
        server_default=CycleCountStatus.PLANNED.value,
    )
    expected_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    counted_qty: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    variance_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    counted_by_user_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    counted_by_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


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
Index("idx_inventory_storage_locations_org", StorageLocationORM.organization_id)
Index("idx_inventory_storage_locations_storeroom", StorageLocationORM.storeroom_id)
Index("idx_inventory_storage_locations_parent", StorageLocationORM.parent_location_id)
Index("idx_inventory_storage_locations_active", StorageLocationORM.is_active)
Index("idx_inventory_reorder_policies_org", ReorderPolicyORM.organization_id)
Index("idx_inventory_reorder_policies_item", ReorderPolicyORM.stock_item_id)
Index("idx_inventory_reorder_policies_storeroom", ReorderPolicyORM.storeroom_id)
Index("idx_inventory_reorder_policies_location", ReorderPolicyORM.location_id)
Index("idx_inventory_cycle_counts_org", CycleCountORM.organization_id)
Index("idx_inventory_cycle_counts_item", CycleCountORM.stock_item_id)
Index("idx_inventory_cycle_counts_storeroom", CycleCountORM.storeroom_id)
Index("idx_inventory_cycle_counts_location", CycleCountORM.location_id)
Index("idx_inventory_cycle_counts_status", CycleCountORM.status)


__all__ = [
    "CycleCountORM",
    "ReorderPolicyORM",
    "StockBalanceORM",
    "StockReservationORM",
    "StockTransactionORM",
    "StorageLocationORM",
    "StoreroomORM",
]
