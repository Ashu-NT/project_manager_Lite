from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.controllers.common import (
    serialize_catalog_detail_view_model,
    serialize_catalog_overview_view_model,
    serialize_record_view_models,
    serialize_selector_options,
    serialize_workspace_view_model,
)


def refresh(ctrl) -> None:
    ctrl._set_is_loading(True)
    try:
        ctrl._set_error_message("")
        ctrl._set_feedback_message("")
        ctrl._set_workspace(
            serialize_workspace_view_model(ctrl._workspace_presenter.build_view_model())
        )
        workspace_state = ctrl._reservations_workspace_presenter.build_workspace_state(
            search_text=ctrl._search_text,
            status_filter=ctrl._selected_status_filter,
            item_filter=ctrl._selected_item_filter,
            storeroom_filter=ctrl._selected_storeroom_filter,
            selected_reservation_id=ctrl._selected_reservation_id or None,
        )
        ctrl._set_overview(
            serialize_catalog_overview_view_model(workspace_state.overview)
        )
        ctrl._set_status_options(
            serialize_selector_options(workspace_state.status_options)
        )
        ctrl._set_item_options(
            serialize_selector_options(workspace_state.item_options)
        )
        ctrl._set_storeroom_options(
            serialize_selector_options(workspace_state.storeroom_options)
        )
        ctrl._set_selected_status_filter(workspace_state.selected_status_filter)
        ctrl._set_selected_item_filter(workspace_state.selected_item_filter)
        ctrl._set_selected_storeroom_filter(workspace_state.selected_storeroom_filter)
        ctrl._set_search_text(workspace_state.search_text)
        ctrl._set_reservations(
            {
                "title": "Reservations",
                "subtitle": (
                    "Manage stock holds, issuing, release, and cancellation flows"
                    " against real upstream demand."
                ),
                "emptyState": workspace_state.empty_state,
                "items": serialize_record_view_models(workspace_state.reservations),
            }
        )
        ctrl._set_selected_reservation_id(workspace_state.selected_reservation_id)
        ctrl._set_selected_reservation(
            serialize_catalog_detail_view_model(
                workspace_state.selected_reservation_detail
            )
        )
        ctrl._set_empty_state(workspace_state.empty_state)
    except Exception as exc:  # pragma: no cover - defensive fallback
        ctrl._set_error_message(str(exc))
    finally:
        ctrl._set_is_loading(False)
