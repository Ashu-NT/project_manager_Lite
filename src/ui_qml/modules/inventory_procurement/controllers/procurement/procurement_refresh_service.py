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
            serialize_workspace_view_model(
                ctrl._workspace_presenter.build_view_model()
            )
        )
        workspace_state = ctrl._procurement_workspace_presenter.build_workspace_state(
            search_text=ctrl._search_text,
            site_filter=ctrl._selected_site_filter,
            storeroom_filter=ctrl._selected_storeroom_filter,
            supplier_filter=ctrl._selected_supplier_filter,
            requisition_status_filter=ctrl._selected_requisition_status_filter,
            purchase_order_status_filter=ctrl._selected_purchase_order_status_filter,
            selected_requisition_id=ctrl._selected_requisition_id or None,
            selected_purchase_order_id=ctrl._selected_purchase_order_id or None,
        )
        ctrl._set_overview(serialize_catalog_overview_view_model(workspace_state.overview))
        ctrl._set_site_options(serialize_selector_options(workspace_state.site_options))
        ctrl._set_storeroom_options(
            serialize_selector_options(workspace_state.storeroom_options)
        )
        ctrl._set_supplier_options(
            serialize_selector_options(workspace_state.supplier_options)
        )
        ctrl._set_requisition_status_options(
            serialize_selector_options(workspace_state.requisition_status_options)
        )
        ctrl._set_purchase_order_status_options(
            serialize_selector_options(workspace_state.purchase_order_status_options)
        )
        ctrl._set_item_options(serialize_selector_options(workspace_state.item_options))
        ctrl._set_requisition_options(
            serialize_selector_options(workspace_state.requisition_options)
        )
        ctrl._set_requisition_line_options(
            serialize_selector_options(workspace_state.requisition_line_options)
        )
        ctrl._set_selected_site_filter(workspace_state.selected_site_filter)
        ctrl._set_selected_storeroom_filter(workspace_state.selected_storeroom_filter)
        ctrl._set_selected_supplier_filter(workspace_state.selected_supplier_filter)
        ctrl._set_selected_requisition_status_filter(
            workspace_state.selected_requisition_status_filter
        )
        ctrl._set_selected_purchase_order_status_filter(
            workspace_state.selected_purchase_order_status_filter
        )
        ctrl._set_search_text(workspace_state.search_text)
        ctrl._set_requisitions(
            {
                "title": "Requisitions",
                "subtitle": (
                    "Capture internal supply demand, add line-level item needs, "
                    "and move draft demand into approvals."
                ),
                "emptyState": workspace_state.requisitions_empty_state,
                "items": serialize_record_view_models(workspace_state.requisitions),
            }
        )
        ctrl._set_selected_requisition_id(workspace_state.selected_requisition_id)
        ctrl._set_selected_requisition(
            serialize_catalog_detail_view_model(
                workspace_state.selected_requisition_detail
            )
        )
        ctrl._set_requisition_lines(
            {
                "title": "Requisition Lines",
                "subtitle": (
                    "Demand lines that will later be converted into supplier-facing "
                    "procurement commitments."
                ),
                "emptyState": workspace_state.requisition_lines_empty_state,
                "items": serialize_record_view_models(workspace_state.requisition_lines),
            }
        )
        ctrl._set_purchase_orders(
            {
                "title": "Purchase Orders",
                "subtitle": (
                    "Commit approved demand to suppliers, track approval state, and "
                    "prepare orders for receiving."
                ),
                "emptyState": workspace_state.purchase_orders_empty_state,
                "items": serialize_record_view_models(workspace_state.purchase_orders),
            }
        )
        ctrl._set_selected_purchase_order_id(workspace_state.selected_purchase_order_id)
        ctrl._set_selected_purchase_order(
            serialize_catalog_detail_view_model(
                workspace_state.selected_purchase_order_detail
            )
        )
        ctrl._set_purchase_order_lines(
            {
                "title": "Purchase-Order Lines",
                "subtitle": (
                    "Receiving destinations, ordered quantities, and outstanding "
                    "supplier commitments on the selected order."
                ),
                "emptyState": workspace_state.purchase_order_lines_empty_state,
                "items": serialize_record_view_models(
                    workspace_state.purchase_order_lines
                ),
            }
        )
        ctrl._set_receipts(
            {
                "title": "Receipt History",
                "subtitle": (
                    "Posted receiving transactions for the selected purchase order, "
                    "including accepted and rejected quantities."
                ),
                "emptyState": workspace_state.receipts_empty_state,
                "items": serialize_record_view_models(workspace_state.receipts),
            }
        )
        ctrl._set_empty_state(workspace_state.empty_state)
    except Exception as exc:  # pragma: no cover - defensive fallback
        ctrl._set_error_message(str(exc))
    finally:
        ctrl._set_is_loading(False)
