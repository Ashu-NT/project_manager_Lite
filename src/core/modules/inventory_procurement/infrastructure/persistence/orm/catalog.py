from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


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


Index("idx_inventory_item_categories_org", InventoryItemCategoryORM.organization_id)
Index("idx_inventory_item_categories_active", InventoryItemCategoryORM.is_active)
Index("idx_inventory_stock_items_org", StockItemORM.organization_id)
Index("idx_inventory_stock_items_active", StockItemORM.is_active)


__all__ = [
    "InventoryItemCategoryORM",
    "StockItemORM",
]
