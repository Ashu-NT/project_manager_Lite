from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.controllers.common import (
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
            serialize_workspace_view_model(
                ctrl._workspace_presenter.build_view_model()
            )
        )
        workspace_state = ctrl._pricing_workspace_presenter.build_workspace_state(
            site_filter=ctrl._selected_site_filter,
            storeroom_filter=ctrl._selected_storeroom_filter,
            supplier_filter=ctrl._selected_supplier_filter,
            limit_filter=ctrl._selected_limit_filter,
        )
        ctrl._set_overview(serialize_catalog_overview_view_model(workspace_state.overview))
        ctrl._set_context_label(workspace_state.context_label)
        ctrl._set_site_options(serialize_selector_options(workspace_state.site_options))
        ctrl._set_storeroom_options(
            serialize_selector_options(workspace_state.storeroom_options)
        )
        ctrl._set_supplier_options(
            serialize_selector_options(workspace_state.supplier_options)
        )
        ctrl._set_limit_options(serialize_selector_options(workspace_state.limit_options))
        ctrl._set_selected_site_filter(workspace_state.selected_site_filter)
        ctrl._set_selected_storeroom_filter(workspace_state.selected_storeroom_filter)
        ctrl._set_selected_supplier_filter(workspace_state.selected_supplier_filter)
        ctrl._set_selected_limit_filter(workspace_state.selected_limit_filter)
        ctrl._set_stock_signals(
            {
                "title": "Stock Status Signals",
                "subtitle": (
                    "Filtered stock rows that matter for replenishment, reserved "
                    "demand, and inbound supply planning."
                ),
                "emptyState": workspace_state.stock_empty_state,
                "items": serialize_record_view_models(workspace_state.stock_rows),
            }
        )
        ctrl._set_supplier_pricing(
            {
                "title": "Supplier Price Lines",
                "subtitle": (
                    "Recent purchase-order lines with unit prices, outstanding "
                    "quantities, and expected delivery context."
                ),
                "emptyState": workspace_state.supplier_price_empty_state,
                "items": serialize_record_view_models(workspace_state.supplier_price_rows),
            }
        )
        ctrl._set_can_export(workspace_state.can_export)
        ctrl._set_empty_state(workspace_state.empty_state)
    except Exception as exc:  # pragma: no cover - defensive fallback
        ctrl._set_error_message(str(exc))
    finally:
        ctrl._set_is_loading(False)
