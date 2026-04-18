from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)

from core.modules.inventory_procurement.domain import StockItem
from src.ui.shared.widgets.code_generation import CodeFieldWidget


_ITEM_STATUSES = ("DRAFT", "ACTIVE", "INACTIVE", "OBSOLETE")


class InventoryItemEditDialog(QDialog):
    def __init__(
        self,
        *,
        item: StockItem | None = None,
        party_options: list[tuple[str, str]] | None = None,
        category_options: list[tuple[str, str]] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._item = item
        self._party_options = list(party_options or [])
        self._category_options = list(category_options or [])
        self.setWindowTitle("Edit Inventory Item" if item is not None else "New Inventory Item")
        self.resize(540, 560)
        self._setup_ui()
        self._load_item()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Capture the operational fields planners and buyers need first. Secondary attributes can stay in later detail slices."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.item_code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.item_code_field = CodeFieldWidget(
            prefix="ITEM",
            line_edit=self.item_code_edit,
            hint_getters=(lambda: self.name_edit.text(),),
        )
        self.status_combo = QComboBox()
        self.status_combo.addItems(_ITEM_STATUSES)
        self.item_type_edit = QLineEdit()
        self.stock_uom_edit = QLineEdit()
        self.order_uom_edit = QLineEdit()
        self.issue_uom_edit = QLineEdit()
        self.category_code_combo = QComboBox()
        for label, category_code in self._category_options:
            self.category_code_combo.addItem(label, category_code)
        if self.category_code_combo.count() == 0:
            self.category_code_combo.addItem("None", "")
        self.reorder_point_spin = QDoubleSpinBox()
        self.reorder_point_spin.setDecimals(3)
        self.reorder_point_spin.setMaximum(999999999)
        self.reorder_qty_spin = QDoubleSpinBox()
        self.reorder_qty_spin.setDecimals(3)
        self.reorder_qty_spin.setMaximum(999999999)
        self.preferred_party_combo = QComboBox()
        for label, party_id in self._party_options:
            self.preferred_party_combo.addItem(label, party_id)
        self.is_stocked_check = QCheckBox("Stocked item")
        self.is_purchase_allowed_check = QCheckBox("Purchasing allowed")
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Short operational notes, handling remarks, or sourcing context.")

        form.addRow("Item Code", self.item_code_field)
        form.addRow("Name", self.name_edit)
        form.addRow("Status", self.status_combo)
        form.addRow("Item Type", self.item_type_edit)
        form.addRow("Stock UOM", self.stock_uom_edit)
        form.addRow("Order UOM", self.order_uom_edit)
        form.addRow("Issue UOM", self.issue_uom_edit)
        form.addRow("Category", self.category_code_combo)
        form.addRow("Reorder Point", self.reorder_point_spin)
        form.addRow("Reorder Qty", self.reorder_qty_spin)
        form.addRow("Preferred Party", self.preferred_party_combo)

        flags_row = QHBoxLayout()
        flags_row.addWidget(self.is_stocked_check)
        flags_row.addWidget(self.is_purchase_allowed_check)
        flags_row.addStretch(1)
        form.addRow("Flags", flags_row)
        form.addRow("Notes", self.notes_edit)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_item(self) -> None:
        item = self._item
        if item is None:
            self.status_combo.setCurrentText("ACTIVE")
            self.stock_uom_edit.setText("EA")
            self.order_uom_edit.setText("EA")
            self.issue_uom_edit.setText("EA")
            self.is_stocked_check.setChecked(True)
            self.is_purchase_allowed_check.setChecked(True)
            return
        self.item_code_edit.setText(item.item_code)
        self.name_edit.setText(item.name)
        self.status_combo.setCurrentText(item.status)
        self.item_type_edit.setText(item.item_type)
        self.stock_uom_edit.setText(item.stock_uom)
        self.order_uom_edit.setText(item.order_uom or item.stock_uom)
        self.issue_uom_edit.setText(item.issue_uom or item.stock_uom)
        self._ensure_combo_option(self.category_code_combo, item.category_code, fallback_label=item.category_code)
        self._set_combo_to_data(self.category_code_combo, item.category_code)
        self.reorder_point_spin.setValue(float(item.reorder_point or 0.0))
        self.reorder_qty_spin.setValue(float(item.reorder_qty or 0.0))
        self._set_combo_to_data(self.preferred_party_combo, item.preferred_party_id or "")
        self.is_stocked_check.setChecked(item.is_stocked)
        self.is_purchase_allowed_check.setChecked(item.is_purchase_allowed)
        self.notes_edit.setPlainText(item.notes)

    @staticmethod
    def _set_combo_to_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @staticmethod
    def _ensure_combo_option(combo: QComboBox, value: str, *, fallback_label: str) -> None:
        normalized = str(value or "").strip()
        if not normalized:
            return
        if combo.findData(normalized) >= 0:
            return
        combo.addItem(fallback_label, normalized)

    @property
    def item_code(self) -> str:
        return self.item_code_edit.text().strip()

    @property
    def name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def status(self) -> str:
        return str(self.status_combo.currentText()).strip().upper()

    @property
    def item_type(self) -> str:
        return self.item_type_edit.text().strip()

    @property
    def stock_uom(self) -> str:
        return self.stock_uom_edit.text().strip()

    @property
    def order_uom(self) -> str:
        return self.order_uom_edit.text().strip()

    @property
    def issue_uom(self) -> str:
        return self.issue_uom_edit.text().strip()

    @property
    def category_code(self) -> str:
        return str(self.category_code_combo.currentData() or "").strip()

    @property
    def reorder_point(self) -> float:
        return float(self.reorder_point_spin.value())

    @property
    def reorder_qty(self) -> float:
        return float(self.reorder_qty_spin.value())

    @property
    def preferred_party_id(self) -> str | None:
        value = str(self.preferred_party_combo.currentData() or "").strip()
        return value or None

    @property
    def is_stocked(self) -> bool:
        return self.is_stocked_check.isChecked()

    @property
    def is_purchase_allowed(self) -> bool:
        return self.is_purchase_allowed_check.isChecked()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()


__all__ = ["InventoryItemEditDialog"]
