from __future__ import annotations

from typing import Any

from src.core.modules.inventory_procurement.api.desktop import (
    InventoryLocationCreateCommand,
    InventoryLocationUpdateCommand,
)

from .validation import optional_bool, optional_int, optional_text, require_text

def create_location(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryLocationCreateCommand(
        storeroom_id=require_text(
            payload,
            "storeroomId",
            "Choose a storeroom before saving a storage location.",
        ),
        location_code=require_text(payload, "locationCode", "Location code is required."),
        name=require_text(payload, "name", "Location name is required."),
        parent_location_id=optional_text(payload, "parentLocationId"),
        location_type=require_text(payload, "locationType", "Location type is required."),
        is_active=optional_bool(payload, "isActive", default=True),
        is_quarantine=optional_bool(payload, "isQuarantine", default=False),
        allows_issue=optional_bool(payload, "allowsIssue", default=True),
        allows_putaway=optional_bool(payload, "allowsPutaway", default=True),
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.create_storage_location(command)

def update_location(desktop_api, payload: dict[str, Any]) -> None:
    command = InventoryLocationUpdateCommand(
        location_id=require_text(
            payload, "locationId", "Location ID is required for updates."
        ),
        location_code=require_text(payload, "locationCode", "Location code is required."),
        name=require_text(payload, "name", "Location name is required."),
        parent_location_id=optional_text(payload, "parentLocationId"),
        location_type=require_text(payload, "locationType", "Location type is required."),
        is_active=optional_bool(payload, "isActive", default=True),
        is_quarantine=optional_bool(payload, "isQuarantine", default=False),
        allows_issue=optional_bool(payload, "allowsIssue", default=True),
        allows_putaway=optional_bool(payload, "allowsPutaway", default=True),
        notes=optional_text(payload, "notes") or "",
        expected_version=optional_int(payload, "expectedVersion"),
    )
    desktop_api.update_storage_location(command)
