from __future__ import annotations


def set_overview(ctrl, overview: dict[str, object]) -> None:
    if overview == ctrl._overview:
        return
    ctrl._overview = overview
    ctrl.overviewChanged.emit()


def set_site_options(ctrl, site_options: list[dict[str, str]]) -> None:
    if site_options == ctrl._site_options:
        return
    ctrl._site_options = site_options
    ctrl.siteOptionsChanged.emit()


def set_storeroom_options(ctrl, storeroom_options: list[dict[str, str]]) -> None:
    if storeroom_options == ctrl._storeroom_options:
        return
    ctrl._storeroom_options = storeroom_options
    ctrl.storeroomOptionsChanged.emit()


def set_supplier_options(ctrl, supplier_options: list[dict[str, str]]) -> None:
    if supplier_options == ctrl._supplier_options:
        return
    ctrl._supplier_options = supplier_options
    ctrl.supplierOptionsChanged.emit()


def set_requisition_status_options(
    ctrl, status_options: list[dict[str, str]]
) -> None:
    if status_options == ctrl._requisition_status_options:
        return
    ctrl._requisition_status_options = status_options
    ctrl.requisitionStatusOptionsChanged.emit()


def set_purchase_order_status_options(
    ctrl, status_options: list[dict[str, str]]
) -> None:
    if status_options == ctrl._purchase_order_status_options:
        return
    ctrl._purchase_order_status_options = status_options
    ctrl.purchaseOrderStatusOptionsChanged.emit()


def set_item_options(ctrl, item_options: list[dict[str, str]]) -> None:
    if item_options == ctrl._item_options:
        return
    ctrl._item_options = item_options
    ctrl.itemOptionsChanged.emit()


def set_requisition_options(
    ctrl, requisition_options: list[dict[str, str]]
) -> None:
    if requisition_options == ctrl._requisition_options:
        return
    ctrl._requisition_options = requisition_options
    ctrl.requisitionOptionsChanged.emit()


def set_requisition_line_options(
    ctrl, requisition_line_options: list[dict[str, str]]
) -> None:
    if requisition_line_options == ctrl._requisition_line_options:
        return
    ctrl._requisition_line_options = requisition_line_options
    ctrl.requisitionLineOptionsChanged.emit()


def set_selected_site_filter(ctrl, selected_site_filter: str) -> None:
    if selected_site_filter == ctrl._selected_site_filter:
        return
    ctrl._selected_site_filter = selected_site_filter
    ctrl.selectedSiteFilterChanged.emit()


def set_selected_storeroom_filter(ctrl, selected_storeroom_filter: str) -> None:
    if selected_storeroom_filter == ctrl._selected_storeroom_filter:
        return
    ctrl._selected_storeroom_filter = selected_storeroom_filter
    ctrl.selectedStoreroomFilterChanged.emit()


def set_selected_supplier_filter(ctrl, selected_supplier_filter: str) -> None:
    if selected_supplier_filter == ctrl._selected_supplier_filter:
        return
    ctrl._selected_supplier_filter = selected_supplier_filter
    ctrl.selectedSupplierFilterChanged.emit()


def set_selected_requisition_status_filter(
    ctrl, selected_requisition_status_filter: str
) -> None:
    if selected_requisition_status_filter == ctrl._selected_requisition_status_filter:
        return
    ctrl._selected_requisition_status_filter = selected_requisition_status_filter
    ctrl.selectedRequisitionStatusFilterChanged.emit()


def set_selected_purchase_order_status_filter(
    ctrl, selected_purchase_order_status_filter: str
) -> None:
    if (
        selected_purchase_order_status_filter
        == ctrl._selected_purchase_order_status_filter
    ):
        return
    ctrl._selected_purchase_order_status_filter = selected_purchase_order_status_filter
    ctrl.selectedPurchaseOrderStatusFilterChanged.emit()


def set_search_text(ctrl, search_text: str) -> None:
    if search_text == ctrl._search_text:
        return
    ctrl._search_text = search_text
    ctrl.searchTextChanged.emit()


def set_requisitions(ctrl, requisitions: dict[str, object]) -> None:
    if requisitions == ctrl._requisitions:
        return
    ctrl._requisitions = requisitions
    ctrl._requisitions_table_model.set_rows(requisitions.get("items", []))
    ctrl.requisitionsChanged.emit()


def set_selected_requisition(
    ctrl, selected_requisition: dict[str, object]
) -> None:
    if selected_requisition == ctrl._selected_requisition:
        return
    ctrl._selected_requisition = selected_requisition
    ctrl.selectedRequisitionChanged.emit()


def set_selected_requisition_id(ctrl, selected_requisition_id: str) -> None:
    if selected_requisition_id == ctrl._selected_requisition_id:
        return
    ctrl._selected_requisition_id = selected_requisition_id
    ctrl.selectedRequisitionIdChanged.emit()


def set_requisition_lines(ctrl, requisition_lines: dict[str, object]) -> None:
    if requisition_lines == ctrl._requisition_lines:
        return
    ctrl._requisition_lines = requisition_lines
    ctrl._requisition_lines_table_model.set_rows(requisition_lines.get("items", []))
    ctrl.requisitionLinesChanged.emit()


def set_purchase_orders(ctrl, purchase_orders: dict[str, object]) -> None:
    if purchase_orders == ctrl._purchase_orders:
        return
    ctrl._purchase_orders = purchase_orders
    ctrl._purchase_orders_table_model.set_rows(purchase_orders.get("items", []))
    ctrl.purchaseOrdersChanged.emit()


def set_selected_purchase_order(
    ctrl, selected_purchase_order: dict[str, object]
) -> None:
    if selected_purchase_order == ctrl._selected_purchase_order:
        return
    ctrl._selected_purchase_order = selected_purchase_order
    ctrl.selectedPurchaseOrderChanged.emit()


def set_selected_purchase_order_id(ctrl, selected_purchase_order_id: str) -> None:
    if selected_purchase_order_id == ctrl._selected_purchase_order_id:
        return
    ctrl._selected_purchase_order_id = selected_purchase_order_id
    ctrl.selectedPurchaseOrderIdChanged.emit()


def set_purchase_order_lines(
    ctrl, purchase_order_lines: dict[str, object]
) -> None:
    if purchase_order_lines == ctrl._purchase_order_lines:
        return
    ctrl._purchase_order_lines = purchase_order_lines
    ctrl._purchase_order_lines_table_model.set_rows(
        purchase_order_lines.get("items", [])
    )
    ctrl.purchaseOrderLinesChanged.emit()


def set_receipts(ctrl, receipts: dict[str, object]) -> None:
    if receipts == ctrl._receipts:
        return
    ctrl._receipts = receipts
    ctrl._receipts_table_model.set_rows(receipts.get("items", []))
    ctrl.receiptsChanged.emit()


def set_selected_requisition_ids(ctrl, ids: list[str]) -> None:
    if ids == ctrl._selected_requisition_ids:
        return
    ctrl._selected_requisition_ids = ids
    ctrl.selectedRequisitionIdsChanged.emit()


def set_selected_purchase_order_ids(ctrl, ids: list[str]) -> None:
    if ids == ctrl._selected_purchase_order_ids:
        return
    ctrl._selected_purchase_order_ids = ids
    ctrl.selectedPurchaseOrderIdsChanged.emit()


def set_detail_activity_items(ctrl, items: list[dict[str, object]]) -> None:
    if items == ctrl._detail_activity_items:
        return
    ctrl._detail_activity_items = items
    ctrl.detailActivityItemsChanged.emit()
