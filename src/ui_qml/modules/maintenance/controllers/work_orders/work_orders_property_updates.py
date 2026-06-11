from __future__ import annotations

from .work_orders_table_models import sync_work_orders_table


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


def set_status_options(controller, options: list) -> None:
    if options == controller._status_options:
        return
    controller._status_options = options
    controller.statusOptionsChanged.emit()


def set_priority_options(controller, options: list) -> None:
    if options == controller._priority_options:
        return
    controller._priority_options = options
    controller.priorityOptionsChanged.emit()


def set_work_order_type_options(controller, options: list) -> None:
    if options == controller._work_order_type_options:
        return
    controller._work_order_type_options = options
    controller.workOrderTypeOptionsChanged.emit()


def set_asset_options(controller, options: list) -> None:
    if options == controller._asset_options:
        return
    controller._asset_options = options
    controller.assetOptionsChanged.emit()


def set_selected_site_filter(controller, value: str) -> None:
    if value == controller._selected_site_filter:
        return
    controller._selected_site_filter = value
    controller.selectedSiteFilterChanged.emit()


def set_selected_status_filter(controller, value: str) -> None:
    if value == controller._selected_status_filter:
        return
    controller._selected_status_filter = value
    controller.selectedStatusFilterChanged.emit()


def set_selected_priority_filter(controller, value: str) -> None:
    if value == controller._selected_priority_filter:
        return
    controller._selected_priority_filter = value
    controller.selectedPriorityFilterChanged.emit()


def set_selected_work_order_type_filter(controller, value: str) -> None:
    if value == controller._selected_work_order_type_filter:
        return
    controller._selected_work_order_type_filter = value
    controller.selectedWorkOrderTypeFilterChanged.emit()


def set_selected_asset_filter(controller, value: str) -> None:
    if value == controller._selected_asset_filter:
        return
    controller._selected_asset_filter = value
    controller.selectedAssetFilterChanged.emit()


def set_search_text_prop(controller, value: str) -> None:
    if value == controller._search_text:
        return
    controller._search_text = value
    controller.searchTextChanged.emit()


def set_work_orders(controller, value: dict) -> None:
    if value == controller._work_orders:
        return
    controller._work_orders = value
    sync_work_orders_table(controller._work_orders_table_model, value)
    controller.workOrdersChanged.emit()


def set_selected_work_order(controller, value: dict) -> None:
    if value == controller._selected_work_order:
        return
    controller._selected_work_order = value
    controller.selectedWorkOrderChanged.emit()


def set_selected_work_order_id(controller, value: str) -> None:
    if value == controller._selected_work_order_id:
        return
    controller._selected_work_order_id = value
    controller.selectedWorkOrderIdChanged.emit()


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


def set_form_system_options(controller, value: list) -> None:
    if value == controller._form_system_options:
        return
    controller._form_system_options = value
    controller.formSystemOptionsChanged.emit()


def set_form_asset_options(controller, value: list) -> None:
    if value == controller._form_asset_options:
        return
    controller._form_asset_options = value
    controller.formAssetOptionsChanged.emit()


def set_form_component_options(controller, value: list) -> None:
    if value == controller._form_component_options:
        return
    controller._form_component_options = value
    controller.formComponentOptionsChanged.emit()


def set_form_source_type_options(controller, value: list) -> None:
    if value == controller._form_source_type_options:
        return
    controller._form_source_type_options = value
    controller.formSourceTypeOptionsChanged.emit()


def set_form_source_work_request_options(controller, value: list) -> None:
    if value == controller._form_source_work_request_options:
        return
    controller._form_source_work_request_options = value
    controller.formSourceWorkRequestOptionsChanged.emit()


def set_form_work_order_type_options(controller, value: list) -> None:
    if value == controller._form_work_order_type_options:
        return
    controller._form_work_order_type_options = value
    controller.formWorkOrderTypeOptionsChanged.emit()


def set_form_priority_options(controller, value: list) -> None:
    if value == controller._form_priority_options:
        return
    controller._form_priority_options = value
    controller.formPriorityOptionsChanged.emit()


def set_form_status_options(controller, value: list) -> None:
    if value == controller._form_status_options:
        return
    controller._form_status_options = value
    controller.formStatusOptionsChanged.emit()


def set_form_employee_options(controller, value: list) -> None:
    if value == controller._form_employee_options:
        return
    controller._form_employee_options = value
    controller.formEmployeeOptionsChanged.emit()


def set_form_vendor_options(controller, value: list) -> None:
    if value == controller._form_vendor_options:
        return
    controller._form_vendor_options = value
    controller.formVendorOptionsChanged.emit()
