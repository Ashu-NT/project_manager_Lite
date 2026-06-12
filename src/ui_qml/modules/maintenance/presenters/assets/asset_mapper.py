from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.assets import (
    MaintenanceAssetLibraryRecordViewModel,
)


def to_asset_record_view_model(row) -> MaintenanceAssetLibraryRecordViewModel:
    return MaintenanceAssetLibraryRecordViewModel(
        id=row.id,
        title=f"{row.asset_code} - {row.name}",
        status_label=row.active_label,
        subtitle=row.system_label or row.location_label,
        supporting_text=(
            f"{row.asset_type or '-'} | {row.asset_category or '-'} | "
            f"{row.criticality_label}"
        ),
        meta_text=f"Lifecycle: {row.status_label}",
        state={
            "assetId": row.id,
            "siteId": row.site_id,
            "locationId": row.location_id,
            "systemId": row.system_id or "",
            "parentAssetId": row.parent_asset_id or "",
            "assetCode": row.asset_code,
            "name": row.name,
            "description": row.description,
            "assetType": row.asset_type,
            "assetCategory": row.asset_category,
            "criticality": row.criticality,
            "status": row.status,
            "manufacturerPartyId": row.manufacturer_party_id or "",
            "supplierPartyId": row.supplier_party_id or "",
            "modelNumber": row.model_number,
            "serialNumber": row.serial_number,
            "barcode": row.barcode,
            "installDate": row.install_date,
            "commissionDate": row.commission_date,
            "warrantyStart": row.warranty_start,
            "warrantyEnd": row.warranty_end,
            "expectedLifeYears": row.expected_life_years if row.expected_life_years is not None else "",
            "replacementCost": row.replacement_cost if row.replacement_cost is not None else "",
            "maintenanceStrategy": row.maintenance_strategy,
            "serviceLevel": row.service_level,
            "requiresShutdownForMajorWork": row.requires_shutdown_for_major_work,
            "isActive": row.is_active,
            "notes": row.notes,
            "expectedVersion": row.version,
            "canPrimaryAction": True,
            "canSecondaryAction": True,
        },
    )
