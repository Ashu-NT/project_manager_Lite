from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryItemCreateCommand,
    InventoryItemUpdateCommand,
)

from .validation import (
    optional_bool,
    optional_float,
    optional_int,
    optional_text,
    require_text,
)


def suggest_item_code(desktop_api, payload: dict[str, Any]) -> str:
    from src.core.platform.common.code_generation import CodeGenerator

    existing = {
        str(getattr(row, "item_code", "") or "").upper()
        for row in desktop_api.list_items(active_only=None)
    }
    name = str(payload.get("name") or "").strip()
    return CodeGenerator().generate(
        "item",
        exists=lambda code: code.upper() in existing,
        name=name or None,
        use_year=not bool(name),
    )


def create_item(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryItemCreateCommand(
        item_code=require_text(payload, "itemCode", "Item code is required."),
        name=require_text(payload, "name", "Item name is required."),
        description=optional_text(payload, "description") or "",
        item_type=optional_text(payload, "itemType") or "",
        status=require_text(payload, "status", "Choose an item status before saving."),
        stock_uom=require_text(payload, "stockUom", "Stock UOM is required."),
        order_uom=optional_text(payload, "orderUom"),
        issue_uom=optional_text(payload, "issueUom"),
        order_uom_ratio=optional_float(payload, "orderUomRatio"),
        issue_uom_ratio=optional_float(payload, "issueUomRatio"),
        category_code=optional_text(payload, "categoryCode") or "",
        commodity_code=optional_text(payload, "commodityCode") or "",
        is_stocked=optional_bool(payload, "isStocked", default=True),
        is_purchase_allowed=optional_bool(payload, "isPurchaseAllowed", default=True),
        default_reorder_policy=optional_text(payload, "defaultReorderPolicy") or "",
        min_qty=optional_float(payload, "minQty", default=0.0) or 0.0,
        max_qty=optional_float(payload, "maxQty", default=0.0) or 0.0,
        reorder_point=optional_float(payload, "reorderPoint", default=0.0) or 0.0,
        reorder_qty=optional_float(payload, "reorderQty", default=0.0) or 0.0,
        lead_time_days=optional_int(payload, "leadTimeDays"),
        is_lot_tracked=optional_bool(payload, "isLotTracked", default=False),
        is_serial_tracked=optional_bool(payload, "isSerialTracked", default=False),
        shelf_life_days=optional_int(payload, "shelfLifeDays"),
        preferred_party_id=optional_text(payload, "preferredPartyId"),
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.create_item(command)


def update_item(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryItemUpdateCommand(
        item_id=require_text(payload, "itemId", "Item ID is required for updates."),
        item_code=require_text(payload, "itemCode", "Item code is required."),
        name=require_text(payload, "name", "Item name is required."),
        description=optional_text(payload, "description") or "",
        item_type=optional_text(payload, "itemType") or "",
        status=require_text(payload, "status", "Choose an item status before saving."),
        stock_uom=require_text(payload, "stockUom", "Stock UOM is required."),
        order_uom=optional_text(payload, "orderUom"),
        issue_uom=optional_text(payload, "issueUom"),
        order_uom_ratio=optional_float(payload, "orderUomRatio"),
        issue_uom_ratio=optional_float(payload, "issueUomRatio"),
        category_code=optional_text(payload, "categoryCode") or "",
        commodity_code=optional_text(payload, "commodityCode") or "",
        is_stocked=optional_bool(payload, "isStocked", default=True),
        is_purchase_allowed=optional_bool(payload, "isPurchaseAllowed", default=True),
        default_reorder_policy=optional_text(payload, "defaultReorderPolicy") or "",
        min_qty=optional_float(payload, "minQty", default=0.0) or 0.0,
        max_qty=optional_float(payload, "maxQty", default=0.0) or 0.0,
        reorder_point=optional_float(payload, "reorderPoint", default=0.0) or 0.0,
        reorder_qty=optional_float(payload, "reorderQty", default=0.0) or 0.0,
        lead_time_days=optional_int(payload, "leadTimeDays"),
        is_lot_tracked=optional_bool(payload, "isLotTracked", default=False),
        is_serial_tracked=optional_bool(payload, "isSerialTracked", default=False),
        shelf_life_days=optional_int(payload, "shelfLifeDays"),
        preferred_party_id=optional_text(payload, "preferredPartyId"),
        notes=optional_text(payload, "notes") or "",
        expected_version=optional_int(payload, "expectedVersion"),
    )
    desktop_api.update_item(command)


def apply_bulk_status(desktop_api, payload: dict[str, Any]) -> None:
    selected_ids = [
        str(item_id or "").strip()
        for item_id in payload.get("itemIds", [])
        if str(item_id or "").strip()
    ]
    if not selected_ids:
        raise ValueError("Select one or more catalog items to update.")
    next_status = require_text(
        payload, "status", "Choose a status before applying the bulk update."
    )
    for item_id in selected_ids:
        desktop_api.change_item_status(item_id, status=next_status)


def toggle_item_active(
    desktop_api,
    item_id: str,
    expected_version: int | None = None,
) -> None:
    normalized_id = (item_id or "").strip()
    if not normalized_id:
        raise ValueError("Item ID is required to change active state.")
    desktop_api.toggle_item_active(normalized_id, expected_version=expected_version)
