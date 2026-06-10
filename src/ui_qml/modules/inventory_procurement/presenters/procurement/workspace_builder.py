from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventorySelectorOptionViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.procurement import (
    InventoryProcurementProcurementWorkspaceViewModel,
)

from .filtering import (
    normalize_filter,
    purchase_order_matches,
    requisition_matches,
)
from .overview_builder import build_overview
from .purchase_order_detail_builder import build_purchase_order_detail
from .purchase_order_line_mapper import to_purchase_order_line_record_view_model
from .purchase_order_mapper import to_purchase_order_record_view_model
from .receipt_mapper import to_receipt_record_view_model
from .requisition_detail_builder import build_requisition_detail
from .requisition_line_mapper import to_requisition_line_record_view_model
from .requisition_mapper import build_requisition_line_options, to_requisition_record_view_model
from .selection import resolve_selected_id


def build_workspace_state(
    desktop_api,
    *,
    search_text: str = "",
    site_filter: str = "all",
    storeroom_filter: str = "all",
    supplier_filter: str = "all",
    requisition_status_filter: str = "all",
    purchase_order_status_filter: str = "all",
    selected_requisition_id: str | None = None,
    selected_purchase_order_id: str | None = None,
) -> InventoryProcurementProcurementWorkspaceViewModel:
    site_options = (
        InventorySelectorOptionViewModel(value="all", label="All sites"),
        *(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_site_options(active_only=None)
        ),
    )
    storeroom_options = (
        InventorySelectorOptionViewModel(value="all", label="All storerooms"),
        *(
            InventorySelectorOptionViewModel(
                value=option.value,
                label=f"{option.label} ({option.site_label})",
            )
            for option in desktop_api.list_storeroom_options(active_only=None)
        ),
    )
    supplier_options = (
        InventorySelectorOptionViewModel(value="all", label="All suppliers"),
        *(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_supplier_options(active_only=None)
        ),
    )
    requisition_status_options = (
        InventorySelectorOptionViewModel(value="all", label="All requisition statuses"),
        *(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_requisition_statuses()
        ),
    )
    purchase_order_status_options = (
        InventorySelectorOptionViewModel(value="all", label="All purchase-order statuses"),
        *(
            InventorySelectorOptionViewModel(value=option.value, label=option.label)
            for option in desktop_api.list_purchase_order_statuses()
        ),
    )
    item_options = tuple(
        InventorySelectorOptionViewModel(value=option.value, label=option.label)
        for option in desktop_api.list_item_options(active_only=None)
    )

    normalized_search = (search_text or "").strip()
    normalized_site_filter = normalize_filter(site_filter, site_options)
    normalized_storeroom_filter = normalize_filter(storeroom_filter, storeroom_options)
    normalized_supplier_filter = normalize_filter(supplier_filter, supplier_options)
    normalized_requisition_status_filter = normalize_filter(
        requisition_status_filter, requisition_status_options
    )
    normalized_purchase_order_status_filter = normalize_filter(
        purchase_order_status_filter, purchase_order_status_options
    )

    all_requisitions = desktop_api.list_requisitions(limit=500)
    filtered_requisitions = tuple(
        row
        for row in desktop_api.list_requisitions(
            status=None
            if normalized_requisition_status_filter == "all"
            else normalized_requisition_status_filter,
            limit=500,
        )
        if requisition_matches(
            row,
            normalized_search,
            normalized_site_filter,
            normalized_storeroom_filter,
        )
    )

    all_purchase_orders = desktop_api.list_purchase_orders(limit=500)
    filtered_purchase_orders = tuple(
        row
        for row in desktop_api.list_purchase_orders(
            status=None
            if normalized_purchase_order_status_filter == "all"
            else normalized_purchase_order_status_filter,
            limit=500,
        )
        if purchase_order_matches(
            row,
            normalized_search,
            normalized_site_filter,
            normalized_supplier_filter,
        )
    )

    all_receipts = desktop_api.list_receipts(limit=500)

    resolved_selected_requisition_id = resolve_selected_id(
        selected_requisition_id, filtered_requisitions
    )
    selected_requisition = next(
        (row for row in filtered_requisitions if row.id == resolved_selected_requisition_id),
        None,
    )
    selected_requisition_lines = (
        desktop_api.list_requisition_lines(selected_requisition.id)
        if selected_requisition is not None
        else ()
    )

    resolved_selected_purchase_order_id = resolve_selected_id(
        selected_purchase_order_id, filtered_purchase_orders
    )
    selected_purchase_order = next(
        (
            row
            for row in filtered_purchase_orders
            if row.id == resolved_selected_purchase_order_id
        ),
        None,
    )
    selected_purchase_order_lines = (
        desktop_api.list_purchase_order_lines(selected_purchase_order.id)
        if selected_purchase_order is not None
        else ()
    )
    selected_receipts = (
        desktop_api.list_receipts(purchase_order_id=selected_purchase_order.id, limit=200)
        if selected_purchase_order is not None
        else ()
    )

    requisition_options = tuple(
        InventorySelectorOptionViewModel(
            value=row.id,
            label=(
                f"{row.requisition_number} | {row.requesting_site_label} | "
                f"{row.status_label}"
            ),
        )
        for row in all_requisitions
        if row.status in {"APPROVED", "PARTIALLY_SOURCED"}
    )
    requisition_line_options = build_requisition_line_options(
        desktop_api,
        selected_purchase_order.source_requisition_id
        if selected_purchase_order is not None
        else None,
    )

    receipt_line_map = {
        receipt.id: desktop_api.list_receipt_lines(receipt.id)
        for receipt in selected_receipts
    }

    return InventoryProcurementProcurementWorkspaceViewModel(
        overview=build_overview(
            all_requisitions=all_requisitions,
            filtered_requisitions=filtered_requisitions,
            all_purchase_orders=all_purchase_orders,
            filtered_purchase_orders=filtered_purchase_orders,
            all_receipts=all_receipts,
        ),
        site_options=site_options,
        storeroom_options=storeroom_options,
        supplier_options=supplier_options,
        requisition_status_options=requisition_status_options,
        purchase_order_status_options=purchase_order_status_options,
        item_options=item_options,
        requisition_options=requisition_options,
        requisition_line_options=requisition_line_options,
        selected_site_filter=normalized_site_filter,
        selected_storeroom_filter=normalized_storeroom_filter,
        selected_supplier_filter=normalized_supplier_filter,
        selected_requisition_status_filter=normalized_requisition_status_filter,
        selected_purchase_order_status_filter=normalized_purchase_order_status_filter,
        search_text=normalized_search,
        requisitions=tuple(
            to_requisition_record_view_model(row) for row in filtered_requisitions
        ),
        selected_requisition_id=resolved_selected_requisition_id,
        selected_requisition_detail=build_requisition_detail(
            selected_requisition, selected_requisition_lines
        ),
        requisition_lines=tuple(
            to_requisition_line_record_view_model(row) for row in selected_requisition_lines
        ),
        requisitions_empty_state=_build_requisitions_empty_state(
            all_requisitions=all_requisitions,
            filtered_requisitions=filtered_requisitions,
            search_text=normalized_search,
            site_filter=normalized_site_filter,
            storeroom_filter=normalized_storeroom_filter,
            status_filter=normalized_requisition_status_filter,
        ),
        requisition_lines_empty_state=_build_requisition_lines_empty_state(
            selected_requisition=selected_requisition,
            selected_requisition_lines=selected_requisition_lines,
        ),
        purchase_orders=tuple(
            to_purchase_order_record_view_model(row) for row in filtered_purchase_orders
        ),
        selected_purchase_order_id=resolved_selected_purchase_order_id,
        selected_purchase_order_detail=build_purchase_order_detail(
            selected_purchase_order, selected_purchase_order_lines
        ),
        purchase_order_lines=tuple(
            to_purchase_order_line_record_view_model(row)
            for row in selected_purchase_order_lines
        ),
        purchase_orders_empty_state=_build_purchase_orders_empty_state(
            all_purchase_orders=all_purchase_orders,
            filtered_purchase_orders=filtered_purchase_orders,
            search_text=normalized_search,
            site_filter=normalized_site_filter,
            supplier_filter=normalized_supplier_filter,
            status_filter=normalized_purchase_order_status_filter,
        ),
        purchase_order_lines_empty_state=_build_purchase_order_lines_empty_state(
            selected_purchase_order=selected_purchase_order,
            selected_purchase_order_lines=selected_purchase_order_lines,
        ),
        receipts=tuple(
            to_receipt_record_view_model(receipt, receipt_line_map.get(receipt.id, ()))
            for receipt in selected_receipts
        ),
        receipts_empty_state=_build_receipts_empty_state(
            selected_purchase_order=selected_purchase_order,
            selected_receipts=selected_receipts,
        ),
        empty_state="",
    )


def _build_requisitions_empty_state(
    *,
    all_requisitions,
    filtered_requisitions,
    search_text: str,
    site_filter: str,
    storeroom_filter: str,
    status_filter: str,
) -> str:
    if filtered_requisitions:
        return ""
    if not all_requisitions:
        return "No requisitions are available yet. Create a requisition to capture upstream inventory demand."
    if search_text or site_filter != "all" or storeroom_filter != "all" or status_filter != "all":
        return "No requisitions match the current filters."
    return "No requisitions are available yet."


def _build_purchase_orders_empty_state(
    *,
    all_purchase_orders,
    filtered_purchase_orders,
    search_text: str,
    site_filter: str,
    supplier_filter: str,
    status_filter: str,
) -> str:
    if filtered_purchase_orders:
        return ""
    if not all_purchase_orders:
        return "No purchase orders are available yet. Convert approved demand into supplier-facing commitments here."
    if search_text or site_filter != "all" or supplier_filter != "all" or status_filter != "all":
        return "No purchase orders match the current filters."
    return "No purchase orders are available yet."


def _build_requisition_lines_empty_state(
    *,
    selected_requisition,
    selected_requisition_lines,
) -> str:
    if selected_requisition is None:
        return "Select a requisition to review or add demand lines."
    if selected_requisition_lines:
        return ""
    return "This requisition does not have any demand lines yet."


def _build_purchase_order_lines_empty_state(
    *,
    selected_purchase_order,
    selected_purchase_order_lines,
) -> str:
    if selected_purchase_order is None:
        return "Select a purchase order to review supplier commitment lines."
    if selected_purchase_order_lines:
        return ""
    return "This purchase order does not have any supplier commitment lines yet."


def _build_receipts_empty_state(
    *,
    selected_purchase_order,
    selected_receipts,
) -> str:
    if selected_purchase_order is None:
        return "Select a purchase order to review receipt history or post receiving transactions."
    if selected_receipts:
        return ""
    return "No receipts have been posted for the selected purchase order yet."
