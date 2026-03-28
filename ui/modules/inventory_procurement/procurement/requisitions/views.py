from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QTableWidgetItem

from core.modules.inventory_procurement.domain import PurchaseRequisition, PurchaseRequisitionStatus
from ui.modules.inventory_procurement.shared.procurement_support import (
    format_date,
    format_item_label,
    format_quantity,
    format_storeroom_label,
    humanize_status,
)
from ui.modules.inventory_procurement.shared.reference_support import (
    build_option_rows,
    format_party_label,
    format_site_label,
)


class RequisitionsViewMixin:
    def _apply_search_filter(self, rows: list[PurchaseRequisition]) -> list[PurchaseRequisition]:
        needle = self.search_text
        if not needle:
            return rows
        filtered: list[PurchaseRequisition] = []
        for row in rows:
            haystacks = (
                row.requisition_number,
                row.purpose,
                row.priority,
                row.requester_username,
                row.status.value,
            )
            if any(needle in str(value or "").lower() for value in haystacks):
                filtered.append(row)
        return filtered

    def _populate_table(self, *, selected_id: str | None) -> None:
        self.table.setRowCount(len(self._rows))
        selected_row = -1
        for row_index, requisition in enumerate(self._rows):
            values = (
                requisition.requisition_number,
                humanize_status(requisition.status.value),
                format_site_label(requisition.requesting_site_id, self._site_lookup),
                format_storeroom_label(requisition.requesting_storeroom_id, self._storeroom_lookup),
                humanize_status(requisition.priority),
                format_date(requisition.needed_by_date),
                requisition.requester_username or "-",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, requisition.id)
                self.table.setItem(row_index, column, item)
            if requisition.id == selected_id:
                selected_row = row_index
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        elif self._rows:
            self.table.selectRow(0)
        else:
            self._selected_lines = []
            self._update_detail(None)

    def _on_selection_changed(self) -> None:
        requisition = self._selected_requisition()
        if requisition is None:
            self._selected_lines = []
            self._update_detail(None)
            self._sync_actions()
            return
        try:
            self._selected_lines = self._procurement_service.list_requisition_lines(requisition.id)
        except Exception:
            self._selected_lines = []
        self._update_detail(requisition)
        self._sync_actions()

    def _update_detail(self, requisition: PurchaseRequisition | None) -> None:
        if requisition is None:
            self.detail_name.setText("Select a requisition")
            self.detail_status.setText("-")
            self.detail_site.setText("-")
            self.detail_storeroom.setText("-")
            self.detail_purpose.setText("-")
            self.detail_needed_by.setText("-")
            self.detail_source.setText("-")
            self.detail_notes.setText("-")
            self.lines_table.setRowCount(0)
            self.selection_badge.setText("Selection: None")
            return
        self.detail_name.setText(requisition.requisition_number)
        self.detail_status.setText(
            f"{humanize_status(requisition.status.value)} | Requester: {requisition.requester_username or '-'}"
        )
        self.detail_site.setText(format_site_label(requisition.requesting_site_id, self._site_lookup))
        self.detail_storeroom.setText(
            format_storeroom_label(requisition.requesting_storeroom_id, self._storeroom_lookup)
        )
        self.detail_purpose.setText(requisition.purpose or "-")
        self.detail_needed_by.setText(format_date(requisition.needed_by_date))
        source_text = requisition.source_reference_type or "-"
        if requisition.source_reference_id:
            source_text = f"{source_text}: {requisition.source_reference_id}"
        self.detail_source.setText(source_text)
        self.detail_notes.setText(requisition.notes or "-")
        self.selection_badge.setText(f"Selection: {requisition.requisition_number}")
        self.lines_table.setRowCount(len(self._selected_lines))
        for row_index, line in enumerate(self._selected_lines):
            values = (
                line.line_number,
                format_item_label(line.stock_item_id, self._item_lookup),
                format_quantity(line.quantity_requested),
                format_quantity(line.quantity_sourced),
                format_party_label(line.suggested_supplier_party_id, self._party_lookup),
                humanize_status(line.status.value),
            )
            for column, value in enumerate(values):
                self.lines_table.setItem(row_index, column, QTableWidgetItem(str(value)))

    def _update_badges(self) -> None:
        awaiting = sum(
            1
            for row in self._rows
            if row.status in {PurchaseRequisitionStatus.SUBMITTED, PurchaseRequisitionStatus.UNDER_REVIEW}
        )
        sourced = sum(
            1
            for row in self._rows
            if row.status in {PurchaseRequisitionStatus.PARTIALLY_SOURCED, PurchaseRequisitionStatus.FULLY_SOURCED}
        )
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.count_badge.setText(f"{len(self._rows)} requisitions")
        self.awaiting_badge.setText(f"{awaiting} awaiting approval")
        self.sourced_badge.setText(f"{sourced} sourced")

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

    def _reload_storeroom_filter(self) -> None:
        current = self._selected_storeroom_filter()
        self.storeroom_filter.blockSignals(True)
        self.storeroom_filter.clear()
        self.storeroom_filter.addItem("All storerooms", None)
        for label, row_id, _site_id in self._storeroom_option_rows():
            self.storeroom_filter.addItem(label, row_id)
        _set_combo_to_data(self.storeroom_filter, current or "")
        self.storeroom_filter.blockSignals(False)

    def _storeroom_option_rows(self) -> list[tuple[str, str, str]]:
        rows: list[tuple[str, str, str]] = []
        for storeroom_id, storeroom in self._storeroom_lookup.items():
            label = (
                f"{format_storeroom_label(storeroom_id, self._storeroom_lookup)}"
                f" ({format_site_label(storeroom.site_id, self._site_lookup)})"
            )
            rows.append((label, storeroom_id, storeroom.site_id))
        return sorted(rows, key=lambda row: row[0].lower())

    def _active_item_options(self) -> list[tuple[str, str]]:
        options: list[tuple[str, str]] = []
        for item_id, item in self._item_lookup.items():
            if not item.is_active or not item.is_purchase_allowed:
                continue
            options.append((format_item_label(item_id, self._item_lookup), item_id))
        return sorted(options, key=lambda row: row[0].lower())

    def _selected_requisition_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        value = str(item.data(Qt.UserRole) or "").strip()
        return value or None

    def _selected_requisition(self) -> PurchaseRequisition | None:
        selected_id = self._selected_requisition_id()
        if not selected_id:
            return None
        for row in self._rows:
            if row.id == selected_id:
                return row
        return None

    def _select_requisition(self, requisition_id: str) -> None:
        for row_index, row in enumerate(self._rows):
            if row.id == requisition_id:
                self.table.selectRow(row_index)
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

    def _selected_storeroom_filter(self) -> str | None:
        value = self.storeroom_filter.currentData()
        return str(value).strip() if value else None

    def _sync_actions(self) -> None:
        requisition = self._selected_requisition()
        is_draft = bool(requisition is not None and requisition.status == PurchaseRequisitionStatus.DRAFT)
        self.btn_edit.setEnabled(self._can_manage and is_draft)
        self.btn_add_line.setEnabled(self._can_manage and is_draft)
        self.btn_cancel.setEnabled(self._can_manage and is_draft)
        self.btn_submit.setEnabled(self._can_manage and is_draft and bool(self._selected_lines))

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
