from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.assets import (
    MaintenanceAssetLibraryDetailFieldViewModel,
    MaintenanceAssetLibraryDetailViewModel,
)

from .system_mapper import to_system_record_view_model


def build_system_detail(row) -> MaintenanceAssetLibraryDetailViewModel:
    if row is None:
        return MaintenanceAssetLibraryDetailViewModel(
            title="No system selected",
            empty_state="Select a system to inspect location scope, lifecycle state, and update actions.",
        )
    return MaintenanceAssetLibraryDetailViewModel(
        id=row.id,
        title=f"{row.system_code} - {row.name}",
        status_label=row.active_label,
        subtitle=row.site_label,
        description=row.description or "No system description provided.",
        fields=(
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Anchor",
                value=row.location_label or "No location assigned",
                supporting_text=row.parent_system_label or "Top-level system",
            ),
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Type / Criticality",
                value=f"{row.system_type or '-'} | {row.criticality_label}",
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
        state=to_system_record_view_model(row).state,
    )
