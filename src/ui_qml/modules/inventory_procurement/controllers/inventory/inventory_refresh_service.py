from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.controllers.common import (
    serialize_catalog_detail_view_model,
    serialize_catalog_overview_view_model,
    serialize_foundation_view_model,
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
            serialize_workspace_view_model(
                ctrl._workspace_presenter.build_view_model()
            )
        )
        workspace_state = ctrl._inventory_workspace_presenter.build_workspace_state(
            search_text=ctrl._search_text,
            site_filter=ctrl._selected_site_filter,
            active_filter=ctrl._selected_active_filter,
            storeroom_filter=ctrl._selected_storeroom_filter,
            item_filter=ctrl._selected_item_filter,
            transaction_type_filter=ctrl._selected_transaction_type_filter,
            selected_storeroom_id=ctrl._selected_storeroom_id or None,
            selected_balance_id=ctrl._selected_balance_id or None,
        )
        ctrl._set_overview(serialize_catalog_overview_view_model(workspace_state.overview))
        ctrl._set_site_options(serialize_selector_options(workspace_state.site_options))
        ctrl._set_active_options(serialize_selector_options(workspace_state.active_options))
        ctrl._set_storeroom_status_options(
            serialize_selector_options(workspace_state.storeroom_status_options)
        )
        ctrl._set_transaction_type_options(
            serialize_selector_options(workspace_state.transaction_type_options)
        )
        ctrl._set_storeroom_options(
            serialize_selector_options(workspace_state.storeroom_options)
        )
        ctrl._set_item_options(serialize_selector_options(workspace_state.item_options))
        ctrl._set_manager_party_options(
            serialize_selector_options(workspace_state.manager_party_options)
        )
        ctrl._set_selected_site_filter(workspace_state.selected_site_filter)
        ctrl._set_selected_active_filter(workspace_state.selected_active_filter)
        ctrl._set_selected_storeroom_filter(workspace_state.selected_storeroom_filter)
        ctrl._set_selected_item_filter(workspace_state.selected_item_filter)
        ctrl._set_selected_transaction_type_filter(
            workspace_state.selected_transaction_type_filter
        )
        ctrl._set_search_text(workspace_state.search_text)
        ctrl._set_storerooms(
            {
                "title": "Storerooms",
                "subtitle": "Govern stock locations, operational permissions, and manager ownership.",
                "emptyState": workspace_state.empty_state,
                "items": serialize_record_view_models(workspace_state.storerooms),
            }
        )
        ctrl._set_selected_storeroom_id(workspace_state.selected_storeroom_id)
        ctrl._set_selected_storeroom(
            serialize_catalog_detail_view_model(workspace_state.selected_storeroom_detail)
        )
        ctrl._set_balances(
            {
                "title": "Stock Balances",
                "subtitle": "Inspect on-hand, reserved, available, and on-order positions by storeroom.",
                "emptyState": workspace_state.empty_state,
                "items": serialize_record_view_models(workspace_state.balances),
            }
        )
        ctrl._set_selected_balance_id(workspace_state.selected_balance_id)
        ctrl._set_selected_balance(
            serialize_catalog_detail_view_model(workspace_state.selected_balance_detail)
        )
        ctrl._set_transactions(
            {
                "title": "Recent Movements",
                "subtitle": "Opening balances, adjustments, issues, returns, and transfer history.",
                "emptyState": workspace_state.empty_state,
                "items": serialize_record_view_models(workspace_state.transactions),
            }
        )
        ctrl._set_foundation(serialize_foundation_view_model(workspace_state.foundation))
        ctrl._set_empty_state(workspace_state.empty_state)
    except Exception as exc:  # pragma: no cover - defensive fallback
        ctrl._set_error_message(str(exc))
    finally:
        ctrl._set_is_loading(False)
