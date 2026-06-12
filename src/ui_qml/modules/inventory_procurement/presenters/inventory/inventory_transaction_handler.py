from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryAdjustmentCommand,
    InventoryIssueCommand,
    InventoryOpeningBalanceCommand,
    InventoryReturnCommand,
    InventoryTransferCommand,
)

from .validation import (
    optional_float,
    optional_text,
    require_positive_float,
    require_text,
)

def post_opening_balance(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryOpeningBalanceCommand(
        stock_item_id=require_text(
            payload, "stockItemId", "Choose an item before posting an opening balance."
        ),
        storeroom_id=require_text(
            payload,
            "storeroomId",
            "Choose a storeroom before posting an opening balance.",
        ),
        quantity=require_positive_float(
            payload, "quantity", "Opening balance quantity must be greater than zero."
        ),
        uom=optional_text(payload, "uom"),
        unit_cost=optional_float(payload, "unitCost", default=0.0) or 0.0,
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.post_opening_balance(command)

def post_adjustment(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryAdjustmentCommand(
        stock_item_id=require_text(
            payload, "stockItemId", "Choose an item before posting an adjustment."
        ),
        storeroom_id=require_text(
            payload, "storeroomId", "Choose a storeroom before posting an adjustment."
        ),
        quantity=require_positive_float(
            payload, "quantity", "Adjustment quantity must be greater than zero."
        ),
        direction=require_text(
            payload,
            "direction",
            "Choose whether the adjustment increases or decreases stock.",
        ),
        uom=optional_text(payload, "uom"),
        unit_cost=optional_float(payload, "unitCost", default=0.0) or 0.0,
        reference_type=optional_text(payload, "referenceType") or "adjustment",
        reference_id=optional_text(payload, "referenceId") or "",
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.post_adjustment(command)

def issue_stock(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryIssueCommand(
        stock_item_id=require_text(
            payload, "stockItemId", "Choose an item before issuing stock."
        ),
        storeroom_id=require_text(
            payload, "storeroomId", "Choose a storeroom before issuing stock."
        ),
        quantity=require_positive_float(
            payload, "quantity", "Issue quantity must be greater than zero."
        ),
        uom=optional_text(payload, "uom"),
        unit_cost=optional_float(payload, "unitCost"),
        release_reserved_qty=optional_float(
            payload, "releaseReservedQty", default=0.0
        ) or 0.0,
        reference_type=optional_text(payload, "referenceType") or "issue",
        reference_id=optional_text(payload, "referenceId") or "",
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.issue_stock(command)

def return_stock(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryReturnCommand(
        stock_item_id=require_text(
            payload, "stockItemId", "Choose an item before posting a return."
        ),
        storeroom_id=require_text(
            payload, "storeroomId", "Choose a storeroom before posting a return."
        ),
        quantity=require_positive_float(
            payload, "quantity", "Return quantity must be greater than zero."
        ),
        uom=optional_text(payload, "uom"),
        unit_cost=optional_float(payload, "unitCost"),
        reference_type=optional_text(payload, "referenceType") or "return",
        reference_id=optional_text(payload, "referenceId") or "",
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.return_stock(command)

def transfer_stock(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryTransferCommand(
        stock_item_id=require_text(
            payload, "stockItemId", "Choose an item before transferring stock."
        ),
        source_storeroom_id=require_text(
            payload,
            "sourceStoreroomId",
            "Choose a source storeroom before transferring stock.",
        ),
        destination_storeroom_id=require_text(
            payload,
            "destinationStoreroomId",
            "Choose a destination storeroom before transferring stock.",
        ),
        quantity=require_positive_float(
            payload, "quantity", "Transfer quantity must be greater than zero."
        ),
        uom=optional_text(payload, "uom"),
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.transfer_stock(command)
