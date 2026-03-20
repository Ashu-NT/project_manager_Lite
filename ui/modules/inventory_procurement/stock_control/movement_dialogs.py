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


class StockMovementDialog(QDialog):
    def __init__(
        self,
        *,
        title: str,
        intro_text: str,
        item_options: list[tuple[str, str]],
        storeroom_options: list[tuple[str, str]],
        reference_type_placeholder: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(500, 420)
        self._setup_ui(
            intro_text=intro_text,
            item_options=item_options,
            storeroom_options=storeroom_options,
            reference_type_placeholder=reference_type_placeholder,
        )

    def _setup_ui(
        self,
        *,
        intro_text: str,
        item_options: list[tuple[str, str]],
        storeroom_options: list[tuple[str, str]],
        reference_type_placeholder: str,
    ) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(intro_text)
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
        self.quantity_spin.setMinimum(0.001)
        self.reference_type_edit = QLineEdit()
        self.reference_type_edit.setPlaceholderText(reference_type_placeholder)
        self.reference_id_edit = QLineEdit()
        self.reference_id_edit.setPlaceholderText("WO-100, TASK-42, RETURN-7, ...")
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Operational note or execution context.")

        form.addRow("Item", self.item_combo)
        form.addRow("Storeroom", self.storeroom_combo)
        form.addRow("Quantity", self.quantity_spin)
        form.addRow("Reference Type", self.reference_type_edit)
        form.addRow("Reference ID", self.reference_id_edit)
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
    def reference_type(self) -> str:
        return self.reference_type_edit.text().strip()

    @property
    def reference_id(self) -> str:
        return self.reference_id_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()


class StockTransferDialog(QDialog):
    def __init__(
        self,
        *,
        item_options: list[tuple[str, str]],
        storeroom_options: list[tuple[str, str]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Transfer Stock")
        self.resize(520, 420)
        self._setup_ui(item_options=item_options, storeroom_options=storeroom_options)

    def _setup_ui(
        self,
        *,
        item_options: list[tuple[str, str]],
        storeroom_options: list[tuple[str, str]],
    ) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Transfer available stock between storerooms in the active organization. The system will post paired outbound and inbound movements."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.item_combo = QComboBox()
        self.source_combo = QComboBox()
        self.destination_combo = QComboBox()
        for label, row_id in item_options:
            self.item_combo.addItem(label, row_id)
        for label, row_id in storeroom_options:
            self.source_combo.addItem(label, row_id)
            self.destination_combo.addItem(label, row_id)
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setDecimals(3)
        self.quantity_spin.setMaximum(999999999)
        self.quantity_spin.setMinimum(0.001)
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Transfer reason or logistics note.")

        form.addRow("Item", self.item_combo)
        form.addRow("Source Storeroom", self.source_combo)
        form.addRow("Destination Storeroom", self.destination_combo)
        form.addRow("Quantity", self.quantity_spin)
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
    def source_storeroom_id(self) -> str:
        return str(self.source_combo.currentData() or "").strip()

    @property
    def destination_storeroom_id(self) -> str:
        return str(self.destination_combo.currentData() or "").strip()

    @property
    def quantity(self) -> float:
        return float(self.quantity_spin.value())

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()


__all__ = ["StockMovementDialog", "StockTransferDialog"]
