from __future__ import annotations

from typing import Any

from src.core.modules.maintenance.api.desktop import (
    MaintenanceLocationCreateCommand,
    MaintenanceLocationUpdateCommand,
)

from .validation import bool_value, optional_text, require_identifier, require_int, require_text

def create_location(desktop_api, payload: dict[str, Any]) -> None:
    command = MaintenanceLocationCreateCommand(
        site_id=require_text(payload, "siteId", "Choose a site before saving."),
        location_code=require_text(payload, "locationCode", "Location code is required."),
        name=require_text(payload, "name", "Location name is required."),
        description=optional_text(payload, "description") or "",
        parent_location_id=optional_text(payload, "parentLocationId"),
        location_type=optional_text(payload, "locationType") or "",
        criticality=require_text(payload, "criticality", "Choose a criticality before saving."),
        status=require_text(payload, "status", "Choose a lifecycle status before saving."),
        is_active=bool_value(payload, "isActive", True),
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.create_location(command)

def update_location(desktop_api, payload: dict[str, Any]) -> None:
    command = MaintenanceLocationUpdateCommand(
        location_id=require_text(payload, "locationId", "Location ID is required before saving."),
        site_id=require_text(payload, "siteId", "Choose a site before saving."),
        location_code=require_text(payload, "locationCode", "Location code is required."),
        name=require_text(payload, "name", "Location name is required."),
        description=optional_text(payload, "description") or "",
        parent_location_id=optional_text(payload, "parentLocationId"),
        location_type=optional_text(payload, "locationType") or "",
        criticality=require_text(payload, "criticality", "Choose a criticality before saving."),
        status=require_text(payload, "status", "Choose a lifecycle status before saving."),
        is_active=bool_value(payload, "isActive", True),
        notes=optional_text(payload, "notes") or "",
        expected_version=require_int(
            payload, "expectedVersion", "Expected version is required before saving."
        ),
    )
    desktop_api.update_location(command)

def toggle_location_active(desktop_api, location_id: str, *, expected_version: int) -> None:
    desktop_api.toggle_location_active(
        require_identifier(location_id, "Location ID is required."),
        expected_version=expected_version,
    )
