from __future__ import annotations


def set_active_view(ctrl, view: str) -> None:
    normalized = view if view in ("stock", "supplier") else "stock"
    if normalized == ctrl._active_view:
        return
    ctrl._active_view = normalized
    ctrl.activeViewChanged.emit()


def select_stock_signal(ctrl, row_id: str) -> None:
    normalized = (row_id or "").strip()
    if normalized == ctrl._selected_stock_signal_id:
        return
    ctrl._selected_stock_signal_id = normalized
    ctrl.selectedStockSignalIdChanged.emit()


def select_supplier_pricing(ctrl, row_id: str) -> None:
    normalized = (row_id or "").strip()
    if normalized == ctrl._selected_supplier_pricing_id:
        return
    ctrl._selected_supplier_pricing_id = normalized
    ctrl.selectedSupplierPricingIdChanged.emit()


def set_stock_signal_page(ctrl, page: int) -> None:
    ctrl._stock_signal_page = max(1, int(page))
    ctrl.stockSignalPageChanged.emit()


def set_stock_signal_page_size(ctrl, size: int) -> None:
    ctrl._stock_signal_page_size = max(10, min(200, int(size)))
    ctrl._stock_signal_page = 1
    ctrl.stockSignalPageSizeChanged.emit()
    ctrl.stockSignalPageChanged.emit()


def set_supplier_pricing_page(ctrl, page: int) -> None:
    ctrl._supplier_pricing_page = max(1, int(page))
    ctrl.supplierPricingPageChanged.emit()


def set_supplier_pricing_page_size(ctrl, size: int) -> None:
    ctrl._supplier_pricing_page_size = max(10, min(200, int(size)))
    ctrl._supplier_pricing_page = 1
    ctrl.supplierPricingPageSizeChanged.emit()
    ctrl.supplierPricingPageChanged.emit()
