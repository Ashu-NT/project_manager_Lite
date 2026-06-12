from __future__ import annotations


def select_requisition(ctrl, requisition_id: str) -> None:
    normalized = (requisition_id or "").strip()
    if normalized == ctrl._selected_requisition_id:
        return
    ctrl._set_selected_requisition_id(normalized)
    ctrl.refresh()


def select_purchase_order(ctrl, purchase_order_id: str) -> None:
    normalized = (purchase_order_id or "").strip()
    if normalized == ctrl._selected_purchase_order_id:
        return
    ctrl._set_selected_purchase_order_id(normalized)
    ctrl.refresh()


def set_active_view(ctrl, view: str) -> None:
    normalized = view if view in ("requisitions", "purchase_orders") else "requisitions"
    if normalized == ctrl._active_view:
        return
    ctrl._active_view = normalized
    ctrl.activeViewChanged.emit()


def set_requisition_page(ctrl, page: int) -> None:
    ctrl._requisition_page = max(1, int(page))
    ctrl.requisitionPageChanged.emit()


def set_requisition_page_size(ctrl, size: int) -> None:
    ctrl._requisition_page_size = max(10, min(200, int(size)))
    ctrl._requisition_page = 1
    ctrl.requisitionPageSizeChanged.emit()
    ctrl.requisitionPageChanged.emit()


def set_purchase_order_page(ctrl, page: int) -> None:
    ctrl._purchase_order_page = max(1, int(page))
    ctrl.purchaseOrderPageChanged.emit()


def set_purchase_order_page_size(ctrl, size: int) -> None:
    ctrl._purchase_order_page_size = max(10, min(200, int(size)))
    ctrl._purchase_order_page = 1
    ctrl.purchaseOrderPageSizeChanged.emit()
    ctrl.purchaseOrderPageChanged.emit()
