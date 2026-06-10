from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.assets import (
    MaintenanceAssetLibraryDetailFieldViewModel,
    MaintenanceAssetLibraryDetailViewModel,
)

from .asset_mapper import to_asset_record_view_model
from .formatting import number_text


def build_asset_detail(row) -> MaintenanceAssetLibraryDetailViewModel:
    if row is None:
        return MaintenanceAssetLibraryDetailViewModel(
            title="No asset selected",
            empty_state="Select an asset to inspect anchor context, lifecycle state, and update actions.",
        )
    return MaintenanceAssetLibraryDetailViewModel(
        id=row.id,
        title=f"{row.asset_code} - {row.name}",
        status_label=row.active_label,
        subtitle=row.site_label,
        description=row.description or "No asset description provided.",
        fields=(
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Anchor",
                value=row.location_label,
                supporting_text=row.system_label or row.parent_asset_label or "No parent asset",
            ),
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Type / Criticality",
                value=f"{row.asset_type or '-'} | {row.asset_category or '-'}",
                supporting_text=(
                    f"{row.criticality_label} | Lifecycle: {row.status_label}"
                ),
            ),
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Vendors",
                value=row.manufacturer_party_label or "-",
                supporting_text=f"Supplier: {row.supplier_party_label or '-'}",
            ),
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Identity",
                value=row.model_number or "-",
                supporting_text=(
                    f"Serial: {row.serial_number or '-'} | Barcode: {row.barcode or '-'}"
                ),
            ),
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Strategy",
                value=row.maintenance_strategy or "-",
                supporting_text=(
                    f"Service level: {row.service_level or '-'} | "
                    f"Replacement cost: {number_text(row.replacement_cost)}"
                ),
            ),
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Dates",
                value=f"Install: {row.install_date or '-'} | Commission: {row.commission_date or '-'}",
                supporting_text=(
                    f"Warranty: {row.warranty_start or '-'} to {row.warranty_end or '-'}"
                ),
            ),
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Notes",
                value=row.notes or "-",
            ),
            MaintenanceAssetLibraryDetailFieldViewModel(
                label="Version",
                value=str(row.version),
                supporting_text=(
                    "Shutdown required for major work"
                    if row.requires_shutdown_for_major_work
                    else "No shutdown requirement flagged"
                ),
            ),
        ),
        state=to_asset_record_view_model(row).state,
    )
