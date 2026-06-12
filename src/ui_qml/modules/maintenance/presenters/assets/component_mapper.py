from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.assets import (
    MaintenanceAssetLibraryRecordViewModel,
)


def to_component_record_view_model(row) -> MaintenanceAssetLibraryRecordViewModel:
    return MaintenanceAssetLibraryRecordViewModel(
        id=row.id,
        title=f"{row.component_code} - {row.name}",
        status_label=row.active_label,
        subtitle=row.asset_label,
        supporting_text=f"{row.component_type or '-'} | {row.status_label}",
        meta_text=(
            "Critical component"
            if row.is_critical_component
            else "Standard component"
        ),
        state={
            "componentId": row.id,
            "assetId": row.asset_id,
            "componentCode": row.component_code,
            "name": row.name,
            "description": row.description,
            "parentComponentId": row.parent_component_id or "",
            "componentType": row.component_type,
            "status": row.status,
            "manufacturerPartyId": row.manufacturer_party_id or "",
            "supplierPartyId": row.supplier_party_id or "",
            "manufacturerPartNumber": row.manufacturer_part_number,
            "supplierPartNumber": row.supplier_part_number,
            "modelNumber": row.model_number,
            "serialNumber": row.serial_number,
            "installDate": row.install_date,
            "warrantyEnd": row.warranty_end,
            "expectedLifeHours": row.expected_life_hours if row.expected_life_hours is not None else "",
            "expectedLifeCycles": row.expected_life_cycles if row.expected_life_cycles is not None else "",
            "isCriticalComponent": row.is_critical_component,
            "isActive": row.is_active,
            "notes": row.notes,
            "expectedVersion": row.version,
            "canPrimaryAction": True,
            "canSecondaryAction": True,
        },
    )
