from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryReorderPolicyUpsertCommand,
)

from .validation import optional_bool, optional_float, optional_int, optional_text, require_text

def upsert_reorder_policy(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryReorderPolicyUpsertCommand(
        stock_item_id=require_text(
            payload, "stockItemId", "Choose an item before saving a reorder policy."
        ),
        storeroom_id=require_text(
            payload, "storeroomId", "Choose a storeroom before saving a reorder policy."
        ),
        location_id=optional_text(payload, "locationId"),
        policy_name=optional_text(payload, "policyName") or "",
        is_active=optional_bool(payload, "isActive", default=True),
        min_qty=optional_float(payload, "minQty", default=0.0) or 0.0,
        max_qty=optional_float(payload, "maxQty", default=0.0) or 0.0,
        reorder_point=optional_float(payload, "reorderPoint", default=0.0) or 0.0,
        reorder_qty=optional_float(payload, "reorderQty", default=0.0) or 0.0,
        economic_order_qty=optional_float(payload, "economicOrderQty", default=0.0) or 0.0,
        lead_time_days=optional_int(payload, "leadTimeDays"),
        review_period_days=optional_int(payload, "reviewPeriodDays"),
        preferred_supplier_party_id=optional_text(payload, "preferredSupplierPartyId"),
        policy_id=optional_text(payload, "policyId"),
        expected_version=optional_int(payload, "expectedVersion"),
    )
    desktop_api.upsert_reorder_policy(command)
