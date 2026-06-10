from __future__ import annotations

from typing import Any

from src.core.modules.maintenance.api.desktop import (
    MaintenanceAssetCreateCommand,
    MaintenanceAssetUpdateCommand,
)

from .validation import (
    bool_value,
    optional_float,
    optional_int,
    optional_text,
    require_identifier,
    require_int,
    require_text,
)


def create_asset(desktop_api, payload: dict[str, Any]) -> None:
    command = MaintenanceAssetCreateCommand(
        site_id=require_text(payload, "siteId", "Choose a site before saving."),
        location_id=require_text(payload, "locationId", "Choose a location before saving."),
        asset_code=require_text(payload, "assetCode", "Asset code is required."),
        name=require_text(payload, "name", "Asset name is required."),
        system_id=optional_text(payload, "systemId"),
        description=optional_text(payload, "description") or "",
        parent_asset_id=optional_text(payload, "parentAssetId"),
        asset_type=optional_text(payload, "assetType") or "",
        asset_category=optional_text(payload, "assetCategory") or "",
        criticality=require_text(payload, "criticality", "Choose a criticality before saving."),
        status=require_text(payload, "status", "Choose a lifecycle status before saving."),
        manufacturer_party_id=optional_text(payload, "manufacturerPartyId"),
        supplier_party_id=optional_text(payload, "supplierPartyId"),
        model_number=optional_text(payload, "modelNumber") or "",
        serial_number=optional_text(payload, "serialNumber") or "",
        barcode=optional_text(payload, "barcode") or "",
        install_date=optional_text(payload, "installDate") or "",
        commission_date=optional_text(payload, "commissionDate") or "",
        warranty_start=optional_text(payload, "warrantyStart") or "",
        warranty_end=optional_text(payload, "warrantyEnd") or "",
        expected_life_years=optional_int(payload, "expectedLifeYears"),
        replacement_cost=optional_float(payload, "replacementCost"),
        maintenance_strategy=optional_text(payload, "maintenanceStrategy") or "",
        service_level=optional_text(payload, "serviceLevel") or "",
        requires_shutdown_for_major_work=bool_value(payload, "requiresShutdownForMajorWork", False),
        is_active=bool_value(payload, "isActive", True),
        notes=optional_text(payload, "notes") or "",
    )
    desktop_api.create_asset(command)


def update_asset(desktop_api, payload: dict[str, Any]) -> None:
    command = MaintenanceAssetUpdateCommand(
        asset_id=require_text(payload, "assetId", "Asset ID is required before saving."),
        site_id=require_text(payload, "siteId", "Choose a site before saving."),
        location_id=require_text(payload, "locationId", "Choose a location before saving."),
        asset_code=require_text(payload, "assetCode", "Asset code is required."),
        name=require_text(payload, "name", "Asset name is required."),
        system_id=optional_text(payload, "systemId"),
        description=optional_text(payload, "description") or "",
        parent_asset_id=optional_text(payload, "parentAssetId"),
        asset_type=optional_text(payload, "assetType") or "",
        asset_category=optional_text(payload, "assetCategory") or "",
        criticality=require_text(payload, "criticality", "Choose a criticality before saving."),
        status=require_text(payload, "status", "Choose a lifecycle status before saving."),
        manufacturer_party_id=optional_text(payload, "manufacturerPartyId"),
        supplier_party_id=optional_text(payload, "supplierPartyId"),
        model_number=optional_text(payload, "modelNumber") or "",
        serial_number=optional_text(payload, "serialNumber") or "",
        barcode=optional_text(payload, "barcode") or "",
        install_date=optional_text(payload, "installDate") or "",
        commission_date=optional_text(payload, "commissionDate") or "",
        warranty_start=optional_text(payload, "warrantyStart") or "",
        warranty_end=optional_text(payload, "warrantyEnd") or "",
        expected_life_years=optional_int(payload, "expectedLifeYears"),
        replacement_cost=optional_float(payload, "replacementCost"),
        maintenance_strategy=optional_text(payload, "maintenanceStrategy") or "",
        service_level=optional_text(payload, "serviceLevel") or "",
        requires_shutdown_for_major_work=bool_value(payload, "requiresShutdownForMajorWork", False),
        is_active=bool_value(payload, "isActive", True),
        notes=optional_text(payload, "notes") or "",
        expected_version=require_int(
            payload, "expectedVersion", "Expected version is required before saving."
        ),
    )
    desktop_api.update_asset(command)


def toggle_asset_active(desktop_api, asset_id: str, *, expected_version: int) -> None:
    desktop_api.toggle_asset_active(
        require_identifier(asset_id, "Asset ID is required."),
        expected_version=expected_version,
    )
