from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.assets import (
    MaintenanceAssetLibraryDetailFieldViewModel,
    MaintenanceAssetLibraryDetailViewModel,
)

from .location_mapper import to_location_record_view_model


def build_location_detail(row) -> MaintenanceAssetLibraryDetailViewModel:
    if row is None:
        return MaintenanceAssetLibraryDetailViewModel(
            title="No location selected",
            empty_state="Select a location to inspect hierarchy, lifecycle state, and update actions.",
        )
    return MaintenanceAssetLibraryDetailViewModel(
        id=row.id,
        title=f"{row.location_code} - {row.name}",
        status_label=row.active_label,
        subtitle=row.site_label,
        description=row.description or "No location description provided.",
        fields=(
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Hierarchy",
                value=row.parent_location_label or "Top-level location",
            ),
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Type / Criticality",
                value=f"{row.location_type or '-'} | {row.criticality_label}",
                supporting_text=f"Lifecycle: {row.status_label}",
            ),
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Notes",
                value=row.notes or "-",
            ),
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Version",
                value=str(row.version),
            ),
        ),
        state=to_location_record_view_model(row).state,
    )
