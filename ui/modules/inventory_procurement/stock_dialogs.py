from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)


class OpeningBalanceDialog(QDialog):
    def __init__(
        self,
        *,
        item_options: list[tuple[str, str]],
        storeroom_options: list[tuple[str, str]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Post Opening Balance")
        self.resize(460, 340)
        self._setup_ui(item_options=item_options, storeroom_options=storeroom_options)

    def _setup_ui(self, *, item_options: list[tuple[str, str]], storeroom_options: list[tuple[str, str]]) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Use opening balance once per stock position to establish the starting on-hand quantity before operational transactions take over."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.item_combo = QComboBox()
        self.storeroom_combo = QComboBox()
        for label, row_id in item_options:
            self.item_combo.addItem(label, row_id)
        for label, row_id in storeroom_options:
            self.storeroom_combo.addItem(label, row_id)
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setDecimals(3)
        self.quantity_spin.setMaximum(999999999)
        self.unit_cost_spin = QDoubleSpinBox()
        self.unit_cost_spin.setDecimals(4)
        self.unit_cost_spin.setMaximum(999999999)
        self.notes_edit = QPlainTextEdit()

        form.addRow("Item", self.item_combo)
        form.addRow("Storeroom", self.storeroom_combo)
        form.addRow("Quantity", self.quantity_spin)
        form.addRow("Unit Cost", self.unit_cost_spin)
        form.addRow("Notes", self.notes_edit)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @property
    def stock_item_id(self) -> str:
        return str(self.item_combo.currentData() or "").strip()

    @property
    def storeroom_id(self) -> str:
        return str(self.storeroom_combo.currentData() or "").strip()

    @property
    def quantity(self) -> float:
        return float(self.quantity_spin.value())

    @property
    def unit_cost(self) -> float:
        return float(self.unit_cost_spin.value())

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()


class StockAdjustmentDialog(QDialog):
    def __init__(
        self,
        *,
        item_options: list[tuple[str, str]],
        storeroom_options: list[tuple[str, str]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Post Stock Adjustment")
        self.resize(460, 360)
        self._setup_ui(item_options=item_options, storeroom_options=storeroom_options)

    def _setup_ui(self, *, item_options: list[tuple[str, str]], storeroom_options: list[tuple[str, str]]) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Adjustments are for controlled corrections. Use them for verified count differences rather than normal operational moves."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.item_combo = QComboBox()
        self.storeroom_combo = QComboBox()
        self.direction_combo = QComboBox()
        self.direction_combo.addItem("Increase", "INCREASE")
        self.direction_combo.addItem("Decrease", "DECREASE")
        for label, row_id in item_options:
            self.item_combo.addItem(label, row_id)
        for label, row_id in storeroom_options:
            self.storeroom_combo.addItem(label, row_id)
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setDecimals(3)
        self.quantity_spin.setMaximum(999999999)
        self.unit_cost_spin = QDoubleSpinBox()
        self.unit_cost_spin.setDecimals(4)
        self.unit_cost_spin.setMaximum(999999999)
        self.reference_id_edit = QLineEdit()
        self.notes_edit = QPlainTextEdit()

        form.addRow("Item", self.item_combo)
        form.addRow("Storeroom", self.storeroom_combo)
        form.addRow("Direction", self.direction_combo)
        form.addRow("Quantity", self.quantity_spin)
        form.addRow("Unit Cost", self.unit_cost_spin)
        form.addRow("Reference Id", self.reference_id_edit)
        form.addRow("Notes", self.notes_edit)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @property
    def stock_item_id(self) -> str:
        return str(self.item_combo.currentData() or "").strip()

    @property
    def storeroom_id(self) -> str:
        return str(self.storeroom_combo.currentData() or "").strip()

    @property
    def direction(self) -> str:
        return str(self.direction_combo.currentData() or "").strip().upper()

    @property
    def quantity(self) -> float:
        return float(self.quantity_spin.value())

    @property
    def unit_cost(self) -> float:
        return float(self.unit_cost_spin.value())

    @property
    def reference_id(self) -> str:
        return self.reference_id_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()


__all__ = ["OpeningBalanceDialog", "StockAdjustmentDialog"]
