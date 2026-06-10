from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryCycleCountCompleteCommand,
    InventoryCycleCountCreateCommand,
)

from .validation import optional_float, optional_int, optional_text, require_text


def schedule_cycle_count(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryCycleCountCreateCommand(
        stock_item_id=require_text(
            payload, "stockItemId", "Choose an item before scheduling a cycle count."
        ),
        storeroom_id=require_text(
            payload, "storeroomId", "Choose a storeroom before scheduling a cycle count."
        ),
        location_id=optional_text(payload, "locationId"),
        scheduled_count_date=optional_text(payload, "scheduledCountDate"),
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.schedule_cycle_count(command)


def complete_cycle_count(desktop_api, payload: dict[str, Any]) -> None:
    counted_qty = optional_float(payload, "countedQty", "Counted quantity must be a valid number.")
    if counted_qty is None or counted_qty < 0:
        raise ValueError("Counted quantity must be zero or greater.")
    command = InventoryCycleCountCompleteCommand(
        cycle_count_id=require_text(payload, "cycleCountId", "Cycle count ID is required."),
        counted_qty=counted_qty,
        notes=optional_text(payload, "notes") or "",
        expected_version=optional_int(payload, "expectedVersion"),
    )
    desktop_api.complete_cycle_count(command)
