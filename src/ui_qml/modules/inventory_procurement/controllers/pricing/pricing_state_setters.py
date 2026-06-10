from __future__ import annotations


def set_overview(ctrl, overview: dict[str, object]) -> None:
    if overview == ctrl._overview:
        return
    ctrl._overview = overview
    ctrl.overviewChanged.emit()


def set_context_label(ctrl, context_label: str) -> None:
    if context_label == ctrl._context_label:
        return
    ctrl._context_label = context_label
    ctrl.contextLabelChanged.emit()


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


def set_limit_options(ctrl, limit_options: list[dict[str, str]]) -> None:
    if limit_options == ctrl._limit_options:
        return
    ctrl._limit_options = limit_options
    ctrl.limitOptionsChanged.emit()


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


def set_selected_limit_filter(ctrl, selected_limit_filter: str) -> None:
    if selected_limit_filter == ctrl._selected_limit_filter:
        return
    ctrl._selected_limit_filter = selected_limit_filter
    ctrl.selectedLimitFilterChanged.emit()


def set_stock_signals(ctrl, stock_signals: dict[str, object]) -> None:
    if stock_signals == ctrl._stock_signals:
        return
    ctrl._stock_signals = stock_signals
    ctrl._stock_signals_table_model.set_rows(stock_signals.get("items", []))
    ctrl.stockSignalsChanged.emit()


def set_supplier_pricing(ctrl, supplier_pricing: dict[str, object]) -> None:
    if supplier_pricing == ctrl._supplier_pricing:
        return
    ctrl._supplier_pricing = supplier_pricing
    ctrl._supplier_pricing_table_model.set_rows(supplier_pricing.get("items", []))
    ctrl.supplierPricingChanged.emit()


def set_can_export(ctrl, can_export: bool) -> None:
    normalized = bool(can_export)
    if normalized == ctrl._can_export:
        return
    ctrl._can_export = normalized
    ctrl.canExportChanged.emit()


def set_detail_activity_items(ctrl, items: list[dict[str, object]]) -> None:
    if items == ctrl._detail_activity_items:
        return
    ctrl._detail_activity_items = items
    ctrl.detailActivityItemsChanged.emit()
