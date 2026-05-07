from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

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


__all__ = [
    "StockBalanceORM",
    "StockReservationORM",
    "StockTransactionORM",
    "StoreroomORM",
]
