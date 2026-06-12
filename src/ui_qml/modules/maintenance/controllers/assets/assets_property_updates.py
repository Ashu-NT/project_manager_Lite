from __future__ import annotations

from .assets_table_models import sync_entity_catalog_table


def set_overview(controller, overview: dict) -> None:
    if overview == controller._overview:
        return
    controller._overview = overview
    controller.overviewChanged.emit()


def set_site_options(controller, options: list) -> None:
    if options == controller._site_options:
        return
    controller._site_options = options
    controller.siteOptionsChanged.emit()


def set_active_filter_options(controller, options: list) -> None:
    if options == controller._active_filter_options:
        return
    controller._active_filter_options = options
    controller.activeFilterOptionsChanged.emit()


def set_selected_site_filter(controller, value: str) -> None:
    if value == controller._selected_site_filter:
        return
    controller._selected_site_filter = value
    controller.selectedSiteFilterChanged.emit()


def set_selected_active_filter(controller, value: str) -> None:
    if value == controller._selected_active_filter:
        return
    controller._selected_active_filter = value
    controller.selectedActiveFilterChanged.emit()


def set_search_text_prop(controller, value: str) -> None:
    if value == controller._search_text:
        return
    controller._search_text = value
    controller.searchTextChanged.emit()


def set_locations(controller, value: dict) -> None:
    if value == controller._locations:
        return
    controller._locations = value
    sync_entity_catalog_table(controller._locations_table_model, value)
    controller.locationsChanged.emit()


def set_systems(controller, value: dict) -> None:
    if value == controller._systems:
        return
    controller._systems = value
    sync_entity_catalog_table(controller._systems_table_model, value)
    controller.systemsChanged.emit()


def set_assets(controller, value: dict) -> None:
    if value == controller._assets:
        return
    controller._assets = value
    sync_entity_catalog_table(controller._assets_table_model, value)
    controller.assetsChanged.emit()


def set_components(controller, value: dict) -> None:
    if value == controller._components:
        return
    controller._components = value
    sync_entity_catalog_table(controller._components_table_model, value)
    controller.componentsChanged.emit()


def set_selected_location(controller, value: dict) -> None:
    if value == controller._selected_location:
        return
    controller._selected_location = value
    controller.selectedLocationChanged.emit()


def set_selected_system(controller, value: dict) -> None:
    if value == controller._selected_system:
        return
    controller._selected_system = value
    controller.selectedSystemChanged.emit()


def set_selected_asset(controller, value: dict) -> None:
    if value == controller._selected_asset:
        return
    controller._selected_asset = value
    controller.selectedAssetChanged.emit()


def set_selected_component(controller, value: dict) -> None:
    if value == controller._selected_component:
        return
    controller._selected_component = value
    controller.selectedComponentChanged.emit()


def set_selected_location_id(controller, value: str) -> None:
    if value == controller._selected_location_id:
        return
    controller._selected_location_id = value
    controller.selectedLocationIdChanged.emit()


def set_selected_system_id(controller, value: str) -> None:
    if value == controller._selected_system_id:
        return
    controller._selected_system_id = value
    controller.selectedSystemIdChanged.emit()


def set_selected_asset_id(controller, value: str) -> None:
    if value == controller._selected_asset_id:
        return
    controller._selected_asset_id = value
    controller.selectedAssetIdChanged.emit()


def set_selected_component_id(controller, value: str) -> None:
    if value == controller._selected_component_id:
        return
    controller._selected_component_id = value
    controller.selectedComponentIdChanged.emit()


def set_form_site_options(controller, value: list) -> None:
    if value == controller._form_site_options:
        return
    controller._form_site_options = value
    controller.formSiteOptionsChanged.emit()


def set_form_location_options(controller, value: list) -> None:
    if value == controller._form_location_options:
        return
    controller._form_location_options = value
    controller.formLocationOptionsChanged.emit()


def set_form_parent_location_options(controller, value: list) -> None:
    if value == controller._form_parent_location_options:
        return
    controller._form_parent_location_options = value
    controller.formParentLocationOptionsChanged.emit()


def set_form_system_options(controller, value: list) -> None:
    if value == controller._form_system_options:
        return
    controller._form_system_options = value
    controller.formSystemOptionsChanged.emit()


def set_form_parent_system_options(controller, value: list) -> None:
    if value == controller._form_parent_system_options:
        return
    controller._form_parent_system_options = value
    controller.formParentSystemOptionsChanged.emit()


def set_form_asset_options(controller, value: list) -> None:
    if value == controller._form_asset_options:
        return
    controller._form_asset_options = value
    controller.formAssetOptionsChanged.emit()


def set_form_parent_asset_options(controller, value: list) -> None:
    if value == controller._form_parent_asset_options:
        return
    controller._form_parent_asset_options = value
    controller.formParentAssetOptionsChanged.emit()


def set_form_component_options(controller, value: list) -> None:
    if value == controller._form_component_options:
        return
    controller._form_component_options = value
    controller.formComponentOptionsChanged.emit()


def set_form_parent_component_options(controller, value: list) -> None:
    if value == controller._form_parent_component_options:
        return
    controller._form_parent_component_options = value
    controller.formParentComponentOptionsChanged.emit()


def set_form_status_options(controller, value: list) -> None:
    if value == controller._form_status_options:
        return
    controller._form_status_options = value
    controller.formStatusOptionsChanged.emit()


def set_form_criticality_options(controller, value: list) -> None:
    if value == controller._form_criticality_options:
        return
    controller._form_criticality_options = value
    controller.formCriticalityOptionsChanged.emit()


def set_form_manufacturer_options(controller, value: list) -> None:
    if value == controller._form_manufacturer_options:
        return
    controller._form_manufacturer_options = value
    controller.formManufacturerOptionsChanged.emit()


def set_form_supplier_options(controller, value: list) -> None:
    if value == controller._form_supplier_options:
        return
    controller._form_supplier_options = value
    controller.formSupplierOptionsChanged.emit()
