from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.assets import (
    MaintenanceAssetLibraryDetailFieldViewModel,
    MaintenanceAssetLibraryDetailViewModel,
)

from .component_mapper import to_component_record_view_model
from .formatting import number_text


def build_component_detail(row) -> MaintenanceAssetLibraryDetailViewModel:
    if row is None:
        return MaintenanceAssetLibraryDetailViewModel(
            title="No component selected",
            empty_state="Select a component to inspect asset scope, lifecycle state, and update actions.",
        )
    return MaintenanceAssetLibraryDetailViewModel(
        id=row.id,
        title=f"{row.component_code} - {row.name}",
        status_label=row.active_label,
        subtitle=row.asset_label,
        description=row.description or "No component description provided.",
        fields=(
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Hierarchy",
                value=row.parent_component_label or "Top-level component",
                supporting_text=f"Type: {row.component_type or '-'}",
            ),
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Lifecycle",
                value=row.status_label,
                supporting_text=(
                    "Critical component"
                    if row.is_critical_component
                    else "Standard component"
                ),
            ),
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Vendors",
                value=row.manufacturer_party_label or "-",
                supporting_text=f"Supplier: {row.supplier_party_label or '-'}",
            ),
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Part numbers",
                value=row.manufacturer_part_number or "-",
                supporting_text=f"Supplier part: {row.supplier_part_number or '-'}",
            ),
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Identity",
                value=row.model_number or "-",
                supporting_text=f"Serial: {row.serial_number or '-'}",
            ),
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Expected life",
                value=number_text(row.expected_life_hours),
                supporting_text=(
                    f"Cycles: {number_text(row.expected_life_cycles)} | "
                    f"Warranty end: {row.warranty_end or '-'}"
                ),
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
        state=to_component_record_view_model(row).state,
    )
