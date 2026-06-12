from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.assets import (
    MaintenanceAssetLibraryRecordViewModel,
)


def to_system_record_view_model(row) -> MaintenanceAssetLibraryRecordViewModel:
    return MaintenanceAssetLibraryRecordViewModel(
        id=row.id,
        title=f"{row.system_code} - {row.name}",
        status_label=row.active_label,
        subtitle=row.location_label or row.site_label,
        supporting_text=f"{row.system_type or '-'} | {row.criticality_label}",
        meta_text=f"Lifecycle: {row.status_label}",
        state={
            "systemId": row.id,
            "siteId": row.site_id,
            "locationId": row.location_id or "",
            "systemCode": row.system_code,
            "name": row.name,
            "description": row.description,
            "parentSystemId": row.parent_system_id or "",
            "parentSystemLabel": row.parent_system_label,
            "systemType": row.system_type,
            "criticality": row.criticality,
            "status": row.status,
            "isActive": row.is_active,
            "notes": row.notes,
            "expectedVersion": row.version,
            "canPrimaryAction": True,
            "canSecondaryAction": True,
        },
    )
