from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.assets import (
    MaintenanceAssetLibraryRecordViewModel,
)


def to_location_record_view_model(row) -> MaintenanceAssetLibraryRecordViewModel:
    return MaintenanceAssetLibraryRecordViewModel(
        id=row.id,
        title=f"{row.location_code} - {row.name}",
        status_label=row.active_label,
        subtitle=row.site_label,
        supporting_text=f"{row.location_type or '-'} | {row.criticality_label}",
        meta_text=f"Lifecycle: {row.status_label}",
        state={
            "locationId": row.id,
            "siteId": row.site_id,
            "siteLabel": row.site_label,
            "locationCode": row.location_code,
            "name": row.name,
            "description": row.description,
            "parentLocationId": row.parent_location_id or "",
            "parentLocationLabel": row.parent_location_label,
            "locationType": row.location_type,
            "criticality": row.criticality,
            "status": row.status,
            "isActive": row.is_active,
            "notes": row.notes,
            "expectedVersion": row.version,
            "canPrimaryAction": True,
            "canSecondaryAction": True,
        },
    )
