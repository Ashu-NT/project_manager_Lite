from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.assets import (
    MaintenanceAssetsWorkspaceViewModel,
)

from .asset_library_serializer import (
    _serialize_asset_library_catalog,
    _serialize_asset_library_detail,
)
from .selector_serializer import serialize_selector_options


def serialize_assets_workspace_state(
    view_model: MaintenanceAssetsWorkspaceViewModel,
) -> dict[str, object]:
    return {
        "overview": {
            "title": view_model.overview.title,
            "subtitle": view_model.overview.subtitle,
            "metrics": [
                {
                    "label": metric.label,
                    "value": metric.value,
                    "supportingText": metric.supporting_text,
                }
                for metric in view_model.overview.metrics
            ],
        },
        "siteOptions": serialize_selector_options(view_model.site_options),
        "activeFilterOptions": serialize_selector_options(
            view_model.active_filter_options
        ),
        "selectedSiteFilter": view_model.selected_site_filter,
        "selectedActiveFilter": view_model.selected_active_filter,
        "searchText": view_model.search_text,
        "locations": _serialize_asset_library_catalog(view_model.locations),
        "systems": _serialize_asset_library_catalog(view_model.systems),
        "assets": _serialize_asset_library_catalog(view_model.assets),
        "components": _serialize_asset_library_catalog(view_model.components),
        "selectedLocationId": view_model.selected_location_id,
        "selectedSystemId": view_model.selected_system_id,
        "selectedAssetId": view_model.selected_asset_id,
        "selectedComponentId": view_model.selected_component_id,
        "selectedLocation": _serialize_asset_library_detail(
            view_model.selected_location_detail
        ),
        "selectedSystem": _serialize_asset_library_detail(
            view_model.selected_system_detail
        ),
        "selectedAsset": _serialize_asset_library_detail(
            view_model.selected_asset_detail
        ),
        "selectedComponent": _serialize_asset_library_detail(
            view_model.selected_component_detail
        ),
        "formSiteOptions": serialize_selector_options(view_model.form_site_options),
        "formLocationOptions": serialize_selector_options(
            view_model.form_location_options
        ),
        "formParentLocationOptions": serialize_selector_options(
            view_model.form_parent_location_options
        ),
        "formSystemOptions": serialize_selector_options(view_model.form_system_options),
        "formParentSystemOptions": serialize_selector_options(
            view_model.form_parent_system_options
        ),
        "formAssetOptions": serialize_selector_options(view_model.form_asset_options),
        "formParentAssetOptions": serialize_selector_options(
            view_model.form_parent_asset_options
        ),
        "formComponentOptions": serialize_selector_options(
            view_model.form_component_options
        ),
        "formParentComponentOptions": serialize_selector_options(
            view_model.form_parent_component_options
        ),
        "formStatusOptions": serialize_selector_options(view_model.form_status_options),
        "formCriticalityOptions": serialize_selector_options(
            view_model.form_criticality_options
        ),
        "formManufacturerOptions": serialize_selector_options(
            view_model.form_manufacturer_options
        ),
        "formSupplierOptions": serialize_selector_options(
            view_model.form_supplier_options
        ),
        "emptyState": view_model.empty_state,
    }


__all__ = ["serialize_assets_workspace_state"]
