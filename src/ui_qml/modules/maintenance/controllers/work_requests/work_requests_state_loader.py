from __future__ import annotations

from src.ui_qml.modules.maintenance.controllers.common import (
    serialize_work_request_workspace_state,
    serialize_workspace_view_model,
)

from .work_requests_property_updates import (
    set_asset_options,
    set_form_asset_options,
    set_form_component_options,
    set_form_location_options,
    set_form_priority_options,
    set_form_site_options,
    set_form_source_type_options,
    set_form_status_options,
    set_form_system_options,
    set_overview,
    set_priority_options,
    set_search_text_prop,
    set_selected_asset_filter,
    set_selected_priority_filter,
    set_selected_site_filter,
    set_selected_status_filter,
    set_selected_work_request,
    set_selected_work_request_id,
    set_site_options,
    set_status_options,
    set_work_requests,
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
        state = serialize_work_request_workspace_state(
            controller._work_requests_workspace_presenter.build_workspace_state(
                search_text=controller._search_text,
                site_filter=controller._selected_site_filter,
                status_filter=controller._selected_status_filter,
                priority_filter=controller._selected_priority_filter,
                asset_filter=controller._selected_asset_filter,
                selected_work_request_id=controller._selected_work_request_id or None,
            )
        )
        set_overview(controller, state["overview"])
        set_site_options(controller, state["siteOptions"])
        set_status_options(controller, state["statusOptions"])
        set_priority_options(controller, state["priorityOptions"])
        set_asset_options(controller, state["assetOptions"])
        set_selected_site_filter(controller, str(state["selectedSiteFilter"]))
        set_selected_status_filter(controller, str(state["selectedStatusFilter"]))
        set_selected_priority_filter(controller, str(state["selectedPriorityFilter"]))
        set_selected_asset_filter(controller, str(state["selectedAssetFilter"]))
        set_search_text_prop(controller, str(state["searchText"]))
        set_work_requests(controller, state["workRequests"])
        set_selected_work_request_id(controller, str(state["selectedWorkRequestId"]))
        set_selected_work_request(controller, state["selectedWorkRequest"])
        set_form_site_options(controller, state["formSiteOptions"])
        set_form_location_options(controller, state["formLocationOptions"])
        set_form_system_options(controller, state["formSystemOptions"])
        set_form_asset_options(controller, state["formAssetOptions"])
        set_form_component_options(controller, state["formComponentOptions"])
        set_form_source_type_options(controller, state["formSourceTypeOptions"])
        set_form_priority_options(controller, state["formPriorityOptions"])
        set_form_status_options(controller, state["formStatusOptions"])
        controller._set_empty_state(str(state["emptyState"]))
    except Exception as exc:  # pragma: no cover - defensive fallback
        controller._set_error_message(str(exc))
    finally:
        controller._set_is_loading(False)
