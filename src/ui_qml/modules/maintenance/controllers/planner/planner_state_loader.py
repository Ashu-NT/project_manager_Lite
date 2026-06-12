from __future__ import annotations

from src.ui_qml.modules.maintenance.controllers.common import (
    serialize_planner_workspace_state,
    serialize_workspace_view_model,
)

from .planner_helpers import normalized_filter
from .planner_property_updates import (
    set_asset_options,
    set_material_rows,
    set_overview,
    set_preventive_rows,
    set_recurring_rows,
    set_request_queue_options,
    set_request_rows,
    set_search_text_prop,
    set_selected_asset_filter,
    set_selected_request_queue,
    set_selected_site_filter,
    set_selected_system_filter,
    set_selected_work_order_queue,
    set_site_options,
    set_system_options,
    set_work_order_queue_options,
    set_work_order_rows,
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
        state = serialize_planner_workspace_state(
            controller._planner_workspace_presenter.build_workspace_state(
                site_id=normalized_filter(controller._selected_site_filter),
                asset_id=normalized_filter(controller._selected_asset_filter),
                system_id=normalized_filter(controller._selected_system_filter),
                request_queue=controller._selected_request_queue,
                work_order_queue=controller._selected_work_order_queue,
                search_text=controller._search_text,
            )
        )
        set_overview(controller, state["overview"])
        set_site_options(controller, state["siteOptions"])
        set_asset_options(controller, state["assetOptions"])
        set_system_options(controller, state["systemOptions"])
        set_request_queue_options(controller, state["requestQueueOptions"])
        set_work_order_queue_options(controller, state["workOrderQueueOptions"])
        set_selected_site_filter(controller, str(state["selectedSiteFilter"]))
        set_selected_asset_filter(controller, str(state["selectedAssetFilter"]))
        set_selected_system_filter(controller, str(state["selectedSystemFilter"]))
        set_selected_request_queue(controller, str(state["selectedRequestQueue"]))
        set_selected_work_order_queue(controller, str(state["selectedWorkOrderQueue"]))
        set_search_text_prop(controller, str(state["searchText"]))
        set_request_rows(controller, state["requestRows"])
        set_work_order_rows(controller, state["workOrderRows"])
        set_material_rows(controller, state["materialRows"])
        set_preventive_rows(controller, state["preventiveRows"])
        set_recurring_rows(controller, state["recurringRows"])
        controller._set_empty_state(str(state["emptyState"]))
    except Exception as exc:  # pragma: no cover - defensive fallback
        controller._set_error_message(str(exc))
    finally:
        controller._set_is_loading(False)
