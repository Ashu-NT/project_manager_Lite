from __future__ import annotations

from src.core.modules.inventory_procurement.domain.catalog.item import (
    InventoryItemCategory,
    StockItem,
)
from src.core.modules.inventory_procurement.infrastructure.persistence.orm.catalog import (
    InventoryItemCategoryORM,
    StockItemORM,
)


def inventory_item_category_to_orm(category: InventoryItemCategory) -> InventoryItemCategoryORM:
    return InventoryItemCategoryORM(
        id=category.id,
        organization_id=category.organization_id,
        category_code=category.category_code,
        name=category.name,
        description=category.description or None,
        category_type=category.category_type,
        is_equipment=category.is_equipment,
        supports_project_usage=category.supports_project_usage,
        supports_maintenance_usage=category.supports_maintenance_usage,
        is_active=category.is_active,
        created_at=category.created_at,
        updated_at=category.updated_at,
        version=getattr(category, "version", 1),
    )


def inventory_item_category_from_orm(obj: InventoryItemCategoryORM) -> InventoryItemCategory:
    return InventoryItemCategory(
        id=obj.id,
        organization_id=obj.organization_id,
        category_code=obj.category_code,
        name=obj.name,
        description=obj.description or "",
        category_type=obj.category_type,
        is_equipment=obj.is_equipment,
        supports_project_usage=obj.supports_project_usage,
        supports_maintenance_usage=obj.supports_maintenance_usage,
        is_active=obj.is_active,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        version=getattr(obj, "version", 1),
    )


def stock_item_to_orm(item: StockItem) -> StockItemORM:
    return StockItemORM(
        id=item.id,
        organization_id=item.organization_id,
        item_code=item.item_code,
        name=item.name,
        description=item.description or None,
        item_type=item.item_type or None,
        status=item.status,
        stock_uom=item.stock_uom,
        order_uom=item.order_uom,
        issue_uom=item.issue_uom,
        order_uom_ratio=item.order_uom_ratio,
        issue_uom_ratio=item.issue_uom_ratio,
        category_code=item.category_code or None,
        commodity_code=item.commodity_code or None,
        is_stocked=item.is_stocked,
        is_purchase_allowed=item.is_purchase_allowed,
        is_active=item.is_active,
        default_reorder_policy=item.default_reorder_policy or None,
        min_qty=item.min_qty,
        max_qty=item.max_qty,
        reorder_point=item.reorder_point,
        reorder_qty=item.reorder_qty,
        lead_time_days=item.lead_time_days,
        is_lot_tracked=item.is_lot_tracked,
        is_serial_tracked=item.is_serial_tracked,
        shelf_life_days=item.shelf_life_days,
        preferred_party_id=item.preferred_party_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        notes=item.notes or None,
        version=getattr(item, "version", 1),
    )


def stock_item_from_orm(obj: StockItemORM) -> StockItem:
    return StockItem(
        id=obj.id,
        organization_id=obj.organization_id,
        item_code=obj.item_code,
        name=obj.name,
        description=obj.description or "",
        item_type=obj.item_type or "",
        status=obj.status,
        stock_uom=obj.stock_uom,
        order_uom=obj.order_uom,
        issue_uom=obj.issue_uom,
        order_uom_ratio=float(obj.order_uom_ratio or 1.0),
        issue_uom_ratio=float(obj.issue_uom_ratio or 1.0),
        category_code=obj.category_code or "",
        commodity_code=obj.commodity_code or "",
        is_stocked=obj.is_stocked,
        is_purchase_allowed=obj.is_purchase_allowed,
        is_active=obj.is_active,
        default_reorder_policy=obj.default_reorder_policy or "",
        min_qty=float(obj.min_qty or 0.0),
        max_qty=float(obj.max_qty or 0.0),
        reorder_point=float(obj.reorder_point or 0.0),
        reorder_qty=float(obj.reorder_qty or 0.0),
        lead_time_days=obj.lead_time_days,
        is_lot_tracked=obj.is_lot_tracked,
        is_serial_tracked=obj.is_serial_tracked,
        shelf_life_days=obj.shelf_life_days,
        preferred_party_id=obj.preferred_party_id,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        notes=obj.notes or "",
        version=getattr(obj, "version", 1),
    )


__all__ = [
    "inventory_item_category_from_orm",
    "inventory_item_category_to_orm",
    "stock_item_from_orm",
    "stock_item_to_orm",
]
