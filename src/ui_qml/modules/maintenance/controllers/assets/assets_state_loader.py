from __future__ import annotations

from src.ui_qml.modules.maintenance.controllers.common import (
    serialize_assets_workspace_state,
    serialize_workspace_view_model,
)

from .assets_property_updates import (
    set_active_filter_options,
    set_assets,
    set_components,
    set_form_asset_options,
    set_form_component_options,
    set_form_criticality_options,
    set_form_location_options,
    set_form_manufacturer_options,
    set_form_parent_asset_options,
    set_form_parent_component_options,
    set_form_parent_location_options,
    set_form_parent_system_options,
    set_form_site_options,
    set_form_status_options,
    set_form_supplier_options,
    set_form_system_options,
    set_locations,
    set_overview,
    set_search_text_prop,
    set_selected_active_filter,
    set_selected_asset,
    set_selected_asset_id,
    set_selected_component,
    set_selected_component_id,
    set_selected_location,
    set_selected_location_id,
    set_selected_site_filter,
    set_selected_system,
    set_selected_system_id,
    set_site_options,
    set_systems,
)


def load_workspace_state(controller) -> None:
    controller._set_is_loading(True)
    try:
        controller._set_error_message("")
        controller._set_feedback_message("")
        controller._set_workspace(
            serialize_workspace_view_model(
                controller._workspace_presenter.build_view_model()
            )
        )
        state = serialize_assets_workspace_state(
            controller._assets_workspace_presenter.build_workspace_state(
                search_text=controller._search_text,
                site_filter=controller._selected_site_filter,
                active_filter=controller._selected_active_filter,
                selected_location_id=controller._selected_location_id or None,
                selected_system_id=controller._selected_system_id or None,
                selected_asset_id=controller._selected_asset_id or None,
                selected_component_id=controller._selected_component_id or None,
            )
        )
        set_overview(controller, state["overview"])
        set_site_options(controller, state["siteOptions"])
        set_active_filter_options(controller, state["activeFilterOptions"])
        set_selected_site_filter(controller, str(state["selectedSiteFilter"]))
        set_selected_active_filter(controller, str(state["selectedActiveFilter"]))
        set_search_text_prop(controller, str(state["searchText"]))
        set_locations(controller, state["locations"])
        set_systems(controller, state["systems"])
        set_assets(controller, state["assets"])
        set_components(controller, state["components"])
        set_selected_location_id(controller, str(state["selectedLocationId"]))
        set_selected_system_id(controller, str(state["selectedSystemId"]))
        set_selected_asset_id(controller, str(state["selectedAssetId"]))
        set_selected_component_id(controller, str(state["selectedComponentId"]))
        set_selected_location(controller, state["selectedLocation"])
        set_selected_system(controller, state["selectedSystem"])
        set_selected_asset(controller, state["selectedAsset"])
        set_selected_component(controller, state["selectedComponent"])
        set_form_site_options(controller, state["formSiteOptions"])
        set_form_location_options(controller, state["formLocationOptions"])
        set_form_parent_location_options(controller, state["formParentLocationOptions"])
        set_form_system_options(controller, state["formSystemOptions"])
        set_form_parent_system_options(controller, state["formParentSystemOptions"])
        set_form_asset_options(controller, state["formAssetOptions"])
        set_form_parent_asset_options(controller, state["formParentAssetOptions"])
        set_form_component_options(controller, state["formComponentOptions"])
        set_form_parent_component_options(controller, state["formParentComponentOptions"])
        set_form_status_options(controller, state["formStatusOptions"])
        set_form_criticality_options(controller, state["formCriticalityOptions"])
        set_form_manufacturer_options(controller, state["formManufacturerOptions"])
        set_form_supplier_options(controller, state["formSupplierOptions"])
        controller._set_empty_state(str(state["emptyState"]))
    except Exception as exc:  # pragma: no cover - defensive fallback
        controller._set_error_message(str(exc))
    finally:
        controller._set_is_loading(False)
