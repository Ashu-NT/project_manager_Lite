from __future__ import annotations

from typing import Any

from src.core.modules.maintenance.api.desktop import (
    MaintenanceSystemCreateCommand,
    MaintenanceSystemUpdateCommand,
)

from .validation import bool_value, optional_text, require_identifier, require_int, require_text


def create_system(desktop_api, payload: dict[str, Any]) -> None:
    command = MaintenanceSystemCreateCommand(
        site_id=require_text(payload, "siteId", "Choose a site before saving."),
        system_code=require_text(payload, "systemCode", "System code is required."),
        name=require_text(payload, "name", "System name is required."),
        location_id=optional_text(payload, "locationId"),
        description=optional_text(payload, "description") or "",
        parent_system_id=optional_text(payload, "parentSystemId"),
        system_type=optional_text(payload, "systemType") or "",
        criticality=require_text(payload, "criticality", "Choose a criticality before saving."),
        status=require_text(payload, "status", "Choose a lifecycle status before saving."),
        is_active=bool_value(payload, "isActive", True),
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.create_system(command)


def update_system(desktop_api, payload: dict[str, Any]) -> None:
    command = MaintenanceSystemUpdateCommand(
        system_id=require_text(payload, "systemId", "System ID is required before saving."),
        site_id=require_text(payload, "siteId", "Choose a site before saving."),
        system_code=require_text(payload, "systemCode", "System code is required."),
        name=require_text(payload, "name", "System name is required."),
        location_id=optional_text(payload, "locationId"),
        description=optional_text(payload, "description") or "",
        parent_system_id=optional_text(payload, "parentSystemId"),
        system_type=optional_text(payload, "systemType") or "",
        criticality=require_text(payload, "criticality", "Choose a criticality before saving."),
        status=require_text(payload, "status", "Choose a lifecycle status before saving."),
        is_active=bool_value(payload, "isActive", True),
        notes=optional_text(payload, "notes") or "",
        expected_version=require_int(
            payload, "expectedVersion", "Expected version is required before saving."
        ),
    )
    desktop_api.update_system(command)


def toggle_system_active(desktop_api, system_id: str, *, expected_version: int) -> None:
    desktop_api.toggle_system_active(
        require_identifier(system_id, "System ID is required."),
        expected_version=expected_version,
    )
