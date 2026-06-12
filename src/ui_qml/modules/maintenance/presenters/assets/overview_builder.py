from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.assets import (
    MaintenanceAssetLibraryMetricViewModel,
    MaintenanceAssetLibraryOverviewViewModel,
)


def build_overview(
    *,
    location_rows,
    system_rows,
    asset_rows,
    component_rows,
    site_filter: str,
    active_filter: str,
) -> MaintenanceAssetLibraryOverviewViewModel:
    scope_text = "All sites" if site_filter == "all" else "Selected site scope"
    state_text = {
        "all": "all lifecycle states",
        "active": "active records only",
        "inactive": "inactive records only",
    }.get(active_filter, "all lifecycle states")
    return MaintenanceAssetLibraryOverviewViewModel(
        title="Assets",
        subtitle=(
            "Maintenance locations, systems, assets, and components now render "
            "through the typed maintenance assets desktop API."
        ),
        metrics=(
            MaintenanceAssetLibraryMetricViewModel(
                label="Locations",
                value=str(len(location_rows)),
                supporting_text=f"{scope_text} | {state_text}",
            ),
            MaintenanceAssetLibraryMetricViewModel(
                label="Systems",
                value=str(len(system_rows)),
                supporting_text="Scoped by the selected location when one is active.",
            ),
            MaintenanceAssetLibraryMetricViewModel(
                label="Assets",
                value=str(len(asset_rows)),
                supporting_text="Scoped by the selected location/system context.",
            ),
            MaintenanceAssetLibraryMetricViewModel(
                label="Components",
                value=str(len(component_rows)),
                supporting_text="Scoped by the selected asset when one is active.",
            ),
        ),
    )
