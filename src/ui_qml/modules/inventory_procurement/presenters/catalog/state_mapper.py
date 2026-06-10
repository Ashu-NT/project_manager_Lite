from __future__ import annotations


def build_category_state(category) -> dict[str, object]:
    return {
        "categoryId": category.id,
        "categoryCode": category.category_code,
        "name": category.name,
        "description": category.description,
        "categoryType": category.category_type,
        "categoryTypeLabel": category.category_type_label,
        "isEquipment": category.is_equipment,
        "supportsProjectUsage": category.supports_project_usage,
        "supportsMaintenanceUsage": category.supports_maintenance_usage,
        "isActive": category.is_active,
        "activeLabel": category.active_label,
        "version": category.version,
    }


def build_item_state(item) -> dict[str, object]:
    return {
        "itemId": item.id,
        "itemCode": item.item_code,
        "name": item.name,
        "description": item.description,
        "itemType": item.item_type,
        "status": item.status,
        "statusLabel": item.status_label,
        "stockUom": item.stock_uom,
        "orderUom": item.order_uom or "",
        "issueUom": item.issue_uom or "",
        "orderUomRatio": f"{float(item.order_uom_ratio or 0.0):.3f}",
        "issueUomRatio": f"{float(item.issue_uom_ratio or 0.0):.3f}",
        "categoryCode": item.category_code,
        "categoryLabel": item.category_label,
        "commodityCode": item.commodity_code,
        "isStocked": item.is_stocked,
        "isPurchaseAllowed": item.is_purchase_allowed,
        "isActive": item.is_active,
        "activeLabel": item.active_label,
        "defaultReorderPolicy": item.default_reorder_policy,
        "minQty": f"{float(item.min_qty or 0.0):.3f}",
        "maxQty": f"{float(item.max_qty or 0.0):.3f}",
        "reorderPoint": f"{float(item.reorder_point or 0.0):.3f}",
        "reorderQty": f"{float(item.reorder_qty or 0.0):.3f}",
        "leadTimeDays": "" if item.lead_time_days is None else str(item.lead_time_days),
        "shelfLifeDays": "" if item.shelf_life_days is None else str(item.shelf_life_days),
        "isLotTracked": item.is_lot_tracked,
        "isSerialTracked": item.is_serial_tracked,
        "preferredPartyId": item.preferred_party_id or "",
        "preferredPartyLabel": item.preferred_party_label or "",
        "notes": item.notes,
        "version": item.version,
    }
