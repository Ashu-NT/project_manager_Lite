from __future__ import annotations

from core.modules.inventory_procurement.domain import StockItem, Storeroom
from infra.platform.db.models import StockItemORM, StoreroomORM


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


def storeroom_to_orm(storeroom: Storeroom) -> StoreroomORM:
    return StoreroomORM(
        id=storeroom.id,
        organization_id=storeroom.organization_id,
        storeroom_code=storeroom.storeroom_code,
        name=storeroom.name,
        description=storeroom.description or None,
        site_id=storeroom.site_id,
        status=storeroom.status,
        storeroom_type=storeroom.storeroom_type or None,
        is_active=storeroom.is_active,
        is_internal_supplier=storeroom.is_internal_supplier,
        allows_issue=storeroom.allows_issue,
        allows_transfer=storeroom.allows_transfer,
        allows_receiving=storeroom.allows_receiving,
        default_currency_code=storeroom.default_currency_code or None,
        manager_party_id=storeroom.manager_party_id,
        created_at=storeroom.created_at,
        updated_at=storeroom.updated_at,
        notes=storeroom.notes or None,
        version=getattr(storeroom, "version", 1),
    )


def storeroom_from_orm(obj: StoreroomORM) -> Storeroom:
    return Storeroom(
        id=obj.id,
        organization_id=obj.organization_id,
        storeroom_code=obj.storeroom_code,
        name=obj.name,
        description=obj.description or "",
        site_id=obj.site_id,
        status=obj.status,
        storeroom_type=obj.storeroom_type or "",
        is_active=obj.is_active,
        is_internal_supplier=obj.is_internal_supplier,
        allows_issue=obj.allows_issue,
        allows_transfer=obj.allows_transfer,
        allows_receiving=obj.allows_receiving,
        default_currency_code=obj.default_currency_code or "",
        manager_party_id=obj.manager_party_id,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        notes=obj.notes or "",
        version=getattr(obj, "version", 1),
    )


__all__ = [
    "stock_item_from_orm",
    "stock_item_to_orm",
    "storeroom_from_orm",
    "storeroom_to_orm",
]
