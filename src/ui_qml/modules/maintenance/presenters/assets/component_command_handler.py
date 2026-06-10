from __future__ import annotations

from typing import Any

from src.core.modules.maintenance.api.desktop import (
    MaintenanceComponentCreateCommand,
    MaintenanceComponentUpdateCommand,
)

from .validation import (
    bool_value,
    optional_int,
    optional_text,
    require_identifier,
    require_int,
    require_text,
)


def create_component(desktop_api, payload: dict[str, Any]) -> None:
    command = MaintenanceComponentCreateCommand(
        asset_id=require_text(payload, "assetId", "Choose an asset before saving."),
        component_code=require_text(payload, "componentCode", "Component code is required."),
        name=require_text(payload, "name", "Component name is required."),
        description=optional_text(payload, "description") or "",
        parent_component_id=optional_text(payload, "parentComponentId"),
        component_type=optional_text(payload, "componentType") or "",
        status=require_text(payload, "status", "Choose a lifecycle status before saving."),
        manufacturer_party_id=optional_text(payload, "manufacturerPartyId"),
        supplier_party_id=optional_text(payload, "supplierPartyId"),
        manufacturer_part_number=optional_text(payload, "manufacturerPartNumber") or "",
        supplier_part_number=optional_text(payload, "supplierPartNumber") or "",
        model_number=optional_text(payload, "modelNumber") or "",
        serial_number=optional_text(payload, "serialNumber") or "",
        install_date=optional_text(payload, "installDate") or "",
        warranty_end=optional_text(payload, "warrantyEnd") or "",
        expected_life_hours=optional_int(payload, "expectedLifeHours"),
        expected_life_cycles=optional_int(payload, "expectedLifeCycles"),
        is_critical_component=bool_value(payload, "isCriticalComponent", False),
        is_active=bool_value(payload, "isActive", True),
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.create_component(command)


def update_component(desktop_api, payload: dict[str, Any]) -> None:
    command = MaintenanceComponentUpdateCommand(
        component_id=require_text(payload, "componentId", "Component ID is required before saving."),
        asset_id=require_text(payload, "assetId", "Choose an asset before saving."),
        component_code=require_text(payload, "componentCode", "Component code is required."),
        name=require_text(payload, "name", "Component name is required."),
        description=optional_text(payload, "description") or "",
        parent_component_id=optional_text(payload, "parentComponentId"),
        component_type=optional_text(payload, "componentType") or "",
        status=require_text(payload, "status", "Choose a lifecycle status before saving."),
        manufacturer_party_id=optional_text(payload, "manufacturerPartyId"),
        supplier_party_id=optional_text(payload, "supplierPartyId"),
        manufacturer_part_number=optional_text(payload, "manufacturerPartNumber") or "",
        supplier_part_number=optional_text(payload, "supplierPartNumber") or "",
        model_number=optional_text(payload, "modelNumber") or "",
        serial_number=optional_text(payload, "serialNumber") or "",
        install_date=optional_text(payload, "installDate") or "",
        warranty_end=optional_text(payload, "warrantyEnd") or "",
        expected_life_hours=optional_int(payload, "expectedLifeHours"),
        expected_life_cycles=optional_int(payload, "expectedLifeCycles"),
        is_critical_component=bool_value(payload, "isCriticalComponent", False),
        is_active=bool_value(payload, "isActive", True),
        notes=optional_text(payload, "notes") or "",
        expected_version=require_int(
            payload, "expectedVersion", "Expected version is required before saving."
        ),
    )
    desktop_api.update_component(command)


def toggle_component_active(desktop_api, component_id: str, *, expected_version: int) -> None:
    desktop_api.toggle_component_active(
        require_identifier(component_id, "Component ID is required."),
        expected_version=expected_version,
    )
