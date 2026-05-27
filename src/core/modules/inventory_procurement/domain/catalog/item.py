from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.core.platform.common.ids import generate_id


@dataclass
class InventoryItemCategory:
    id: str
    organization_id: str
    category_code: str
    name: str
    description: str = ""
    category_type: str = "MATERIAL"
    is_equipment: bool = False
    supports_project_usage: bool = False
    supports_maintenance_usage: bool = False
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        category_code: str,
        name: str,
        description: str = "",
        category_type: str = "MATERIAL",
        is_equipment: bool = False,
        supports_project_usage: bool = False,
        supports_maintenance_usage: bool = False,
        is_active: bool = True,
    ) -> "InventoryItemCategory":
        now = datetime.now(timezone.utc)
        return InventoryItemCategory(
            id=generate_id(),
            organization_id=organization_id,
            category_code=category_code,
            name=name,
            description=description,
            category_type=category_type,
            is_equipment=is_equipment,
            supports_project_usage=supports_project_usage,
            supports_maintenance_usage=supports_maintenance_usage,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            version=1,
        )


@dataclass
class StockItem:
    id: str
    organization_id: str
    item_code: str
    name: str
    description: str = ""
    item_type: str = ""
    status: str = "DRAFT"
    stock_uom: str = ""
    order_uom: str = ""
    issue_uom: str = ""
    order_uom_ratio: float = 1.0
    issue_uom_ratio: float = 1.0
    category_code: str = ""
    commodity_code: str = ""
    is_stocked: bool = True
    is_purchase_allowed: bool = True
    is_active: bool = False
    default_reorder_policy: str = ""
    min_qty: float = 0.0
    max_qty: float = 0.0
    reorder_point: float = 0.0
    reorder_qty: float = 0.0
    lead_time_days: int | None = None
    is_lot_tracked: bool = False
    is_serial_tracked: bool = False
    shelf_life_days: int | None = None
    preferred_party_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        item_code: str,
        name: str,
        description: str = "",
        item_type: str = "",
        status: str = "DRAFT",
        stock_uom: str,
        order_uom: str = "",
        issue_uom: str = "",
        order_uom_ratio: float = 1.0,
        issue_uom_ratio: float = 1.0,
        category_code: str = "",
        commodity_code: str = "",
        is_stocked: bool = True,
        is_purchase_allowed: bool = True,
        is_active: bool = False,
        default_reorder_policy: str = "",
        min_qty: float = 0.0,
        max_qty: float = 0.0,
        reorder_point: float = 0.0,
        reorder_qty: float = 0.0,
        lead_time_days: int | None = None,
        is_lot_tracked: bool = False,
        is_serial_tracked: bool = False,
        shelf_life_days: int | None = None,
        preferred_party_id: str | None = None,
        notes: str = "",
    ) -> "StockItem":
        now = datetime.now(timezone.utc)
        return StockItem(
            id=generate_id(),
            organization_id=organization_id,
            item_code=item_code,
            name=name,
            description=description,
            item_type=item_type,
            status=status,
            stock_uom=stock_uom,
            order_uom=order_uom,
            issue_uom=issue_uom,
            order_uom_ratio=order_uom_ratio,
            issue_uom_ratio=issue_uom_ratio,
            category_code=category_code,
            commodity_code=commodity_code,
            is_stocked=is_stocked,
            is_purchase_allowed=is_purchase_allowed,
            is_active=is_active,
            default_reorder_policy=default_reorder_policy,
            min_qty=min_qty,
            max_qty=max_qty,
            reorder_point=reorder_point,
            reorder_qty=reorder_qty,
            lead_time_days=lead_time_days,
            is_lot_tracked=is_lot_tracked,
            is_serial_tracked=is_serial_tracked,
            shelf_life_days=shelf_life_days,
            preferred_party_id=preferred_party_id,
            created_at=now,
            updated_at=now,
            notes=notes,
            version=1,
        )
