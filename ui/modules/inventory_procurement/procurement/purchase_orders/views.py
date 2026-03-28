from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QTableWidgetItem

from core.modules.inventory_procurement.domain import PurchaseOrder, PurchaseOrderStatus, PurchaseRequisitionStatus
from ui.modules.inventory_procurement.shared.procurement_support import (
    format_date,
    format_item_label,
    format_quantity,
    format_requisition_label,
    format_storeroom_label,
    humanize_status,
)
from ui.modules.inventory_procurement.shared.reference_support import (
    build_option_rows,
    format_party_label,
    format_site_label,
)


class PurchaseOrdersViewMixin:
    def _apply_search_filter(self, rows: list[PurchaseOrder]) -> list[PurchaseOrder]:
        needle = self.search_text
        if not needle:
            return rows
        filtered: list[PurchaseOrder] = []
        for row in rows:
            haystacks = (
                row.po_number,
                row.currency_code,
                row.supplier_reference,
                row.status.value,
                format_party_label(row.supplier_party_id, self._party_lookup),
            )
            if any(needle in str(value or "").lower() for value in haystacks):
                filtered.append(row)
        return filtered

    def _populate_table(self, *, selected_id: str | None) -> None:
        self.table.setRowCount(len(self._rows))
        selected_row = -1
        for row_index, purchase_order in enumerate(self._rows):
            values = (
                purchase_order.po_number,
                humanize_status(purchase_order.status.value),
                format_site_label(purchase_order.site_id, self._site_lookup),
                format_party_label(purchase_order.supplier_party_id, self._party_lookup),
                purchase_order.currency_code or "-",
                format_date(purchase_order.expected_delivery_date),
                format_requisition_label(purchase_order.source_requisition_id, self._requisition_lookup),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, purchase_order.id)
                self.table.setItem(row_index, column, item)
            if purchase_order.id == selected_id:
                selected_row = row_index
        if selected_row >= 0:
            self.table.selectRow(selected_row)
            self._on_selection_changed()
        elif self._rows:
            self.table.selectRow(0)
            self._on_selection_changed()
        else:
            self._selected_lines = []
            self._update_detail(None)

    def _on_selection_changed(self) -> None:
        purchase_order = self._selected_purchase_order()
        if purchase_order is None:
            self._selected_lines = []
            self._update_detail(None)
            self._sync_actions()
            return
        try:
            self._selected_lines = self._purchasing_service.list_purchase_order_lines(purchase_order.id)
        except Exception:
            self._selected_lines = []
        self._update_detail(purchase_order)
        self._sync_actions()

    def _update_detail(self, purchase_order: PurchaseOrder | None) -> None:
        if purchase_order is None:
            self.detail_name.setText("Select a purchase order")
            self.detail_status.setText("-")
            self.detail_site.setText("-")
            self.detail_supplier.setText("-")
            self.detail_currency.setText("-")
            self.detail_delivery.setText("-")
            self.detail_source.setText("-")
            self.detail_notes.setText("-")
            self.lines_table.setRowCount(0)
            self.selection_badge.setText("Selection: None")
            return
        self.detail_name.setText(purchase_order.po_number)
        self.detail_status.setText(
            f"{humanize_status(purchase_order.status.value)} | Supplier Ref: {purchase_order.supplier_reference or '-'}"
        )
        self.detail_site.setText(format_site_label(purchase_order.site_id, self._site_lookup))
        self.detail_supplier.setText(format_party_label(purchase_order.supplier_party_id, self._party_lookup))
        self.detail_currency.setText(purchase_order.currency_code or "-")
        delivery_text = f"Expected {format_date(purchase_order.expected_delivery_date)}"
        if purchase_order.order_date:
            delivery_text = f"Ordered {format_date(purchase_order.order_date)} | {delivery_text}"
        self.detail_delivery.setText(delivery_text)
        self.detail_source.setText(format_requisition_label(purchase_order.source_requisition_id, self._requisition_lookup))
        self.detail_notes.setText(purchase_order.notes or "-")
        self.selection_badge.setText(f"Selection: {purchase_order.po_number}")
        self.lines_table.setRowCount(len(self._selected_lines))
        for row_index, line in enumerate(self._selected_lines):
            values = (
                line.line_number,
                format_item_label(line.stock_item_id, self._item_lookup),
                format_storeroom_label(line.destination_storeroom_id, self._storeroom_lookup),
                format_quantity(line.quantity_ordered),
                format_quantity(line.quantity_received),
                format_quantity(line.quantity_rejected),
                humanize_status(line.status.value),
            )
            for column, value in enumerate(values):
                self.lines_table.setItem(row_index, column, QTableWidgetItem(str(value)))

    def _update_badges(self) -> None:
        awaiting = sum(
            1
            for row in self._rows
            if row.status in {PurchaseOrderStatus.SUBMITTED, PurchaseOrderStatus.UNDER_REVIEW}
        )
        open_receiving = sum(
            1
            for row in self._rows
            if row.status in {PurchaseOrderStatus.APPROVED, PurchaseOrderStatus.SENT, PurchaseOrderStatus.PARTIALLY_RECEIVED}
        )
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.count_badge.setText(f"{len(self._rows)} purchase orders")
        self.awaiting_badge.setText(f"{awaiting} awaiting approval")
        self.receiving_badge.setText(f"{open_receiving} open for receiving")

    def _reload_site_filter(self) -> None:
        current = self._selected_site_filter()
        self.site_filter.blockSignals(True)
        self.site_filter.clear()
        self.site_filter.addItem("All sites", None)
        for label, row_id in build_option_rows(
            {site_id: format_site_label(site_id, self._site_lookup) for site_id in self._site_lookup}
        ):
            self.site_filter.addItem(label, row_id)
        _set_combo_to_data(self.site_filter, current or "")
        self.site_filter.blockSignals(False)

    def _reload_supplier_filter(self) -> None:
        current = self._selected_supplier_filter()
        self.supplier_filter.blockSignals(True)
        self.supplier_filter.clear()
        self.supplier_filter.addItem("All suppliers", None)
        for label, row_id in build_option_rows(
            {party_id: format_party_label(party_id, self._party_lookup) for party_id in self._party_lookup}
        ):
            self.supplier_filter.addItem(label, row_id)
        _set_combo_to_data(self.supplier_filter, current or "")
        self.supplier_filter.blockSignals(False)

    def _requisition_options(self) -> list[tuple[str, str]]:
        options: list[tuple[str, str]] = []
        for requisition_id, requisition in self._requisition_lookup.items():
            if requisition.status not in {
                PurchaseRequisitionStatus.APPROVED,
                PurchaseRequisitionStatus.PARTIALLY_SOURCED,
            }:
                continue
            label = (
                f"{requisition.requisition_number} | "
                f"{format_site_label(requisition.requesting_site_id, self._site_lookup)} | "
                f"{humanize_status(requisition.status.value)}"
            )
            options.append((label, requisition_id))
        return sorted(options, key=lambda row: row[0].lower())

    def _requisition_line_options(self, requisition_id: str | None) -> list[tuple[str, str]]:
        if not requisition_id:
            return []
        try:
            lines = self._procurement_service.list_requisition_lines(requisition_id)
        except Exception:
            return []
        options: list[tuple[str, str]] = []
        for line in lines:
            remaining = max(0.0, float(line.quantity_requested or 0.0) - float(line.quantity_sourced or 0.0))
            if remaining <= 0:
                continue
            label = (
                f"L{line.line_number} | {format_item_label(line.stock_item_id, self._item_lookup)} | "
                f"Remaining {format_quantity(remaining)}"
            )
            options.append((label, line.id))
        return sorted(options, key=lambda row: row[0].lower())

    def _storeroom_options_for_site(self, site_id: str) -> list[tuple[str, str]]:
        options: list[tuple[str, str]] = []
        for storeroom_id, storeroom in self._storeroom_lookup.items():
            if storeroom.site_id != site_id:
                continue
            options.append((format_storeroom_label(storeroom_id, self._storeroom_lookup), storeroom_id))
        return sorted(options, key=lambda row: row[0].lower())

    def _active_item_options(self) -> list[tuple[str, str]]:
        options: list[tuple[str, str]] = []
        for item_id, item in self._item_lookup.items():
            if not item.is_active or not item.is_purchase_allowed:
                continue
            options.append((format_item_label(item_id, self._item_lookup), item_id))
        return sorted(options, key=lambda row: row[0].lower())

    def _selected_purchase_order_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        value = str(item.data(Qt.UserRole) or "").strip()
        return value or None

    def _selected_purchase_order(self) -> PurchaseOrder | None:
        selected_id = self._selected_purchase_order_id()
        if not selected_id:
            return None
        for row in self._rows:
            if row.id == selected_id:
                return row
        return None

    def _select_purchase_order(self, purchase_order_id: str) -> None:
        for row_index, row in enumerate(self._rows):
            if row.id == purchase_order_id:
                self.table.selectRow(row_index)
                try:
                    self._selected_lines = self._purchasing_service.list_purchase_order_lines(row.id)
                except Exception:
                    self._selected_lines = []
                self._update_detail(row)
                self._sync_actions()
                return

    @property
    def search_text(self) -> str:
        return self.search_edit.text().strip().lower()

    def _selected_status_filter(self) -> str | None:
        value = self.status_filter.currentData()
        return str(value).strip() if value else None

    def _selected_site_filter(self) -> str | None:
        value = self.site_filter.currentData()
        return str(value).strip() if value else None

    def _selected_supplier_filter(self) -> str | None:
        value = self.supplier_filter.currentData()
        return str(value).strip() if value else None

    def _sync_actions(self) -> None:
        purchase_order = self._selected_purchase_order()
        is_draft = bool(purchase_order is not None and purchase_order.status == PurchaseOrderStatus.DRAFT)
        can_send = bool(purchase_order is not None and purchase_order.status == PurchaseOrderStatus.APPROVED)
        can_close = bool(
            purchase_order is not None
            and purchase_order.status
            in {
                PurchaseOrderStatus.APPROVED,
                PurchaseOrderStatus.SENT,
                PurchaseOrderStatus.PARTIALLY_RECEIVED,
                PurchaseOrderStatus.FULLY_RECEIVED,
            }
            and _is_fully_processed(self._selected_lines)
        )
        self.btn_edit.setEnabled(self._can_manage and is_draft)
        self.btn_add_line.setEnabled(self._can_manage and is_draft)
        self.btn_cancel.setEnabled(self._can_manage and is_draft)
        self.btn_submit.setEnabled(self._can_manage and is_draft and bool(self._selected_lines))
        self.btn_send.setEnabled(self._can_manage and can_send)
        self.btn_close.setEnabled(self._can_manage and can_close)

    def _context_label(self) -> str:
        site_label = "All sites"
        site_id = self._selected_site_filter()
        if site_id:
            site_label = format_site_label(site_id, self._site_lookup)
        status_label = humanize_status(self._selected_status_filter() or "all")
        return f"{site_label} | {status_label}"


def _set_combo_to_data(combo: QComboBox, value: str) -> None:
    if not value:
        return
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)


def _is_fully_processed(lines) -> bool:
    return bool(lines) and all(
        max(
            0.0,
            float(line.quantity_ordered or 0.0)
            - float(line.quantity_received or 0.0)
            - float(line.quantity_rejected or 0.0),
        )
        <= 0
        for line in lines
    )
