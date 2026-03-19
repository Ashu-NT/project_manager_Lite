from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)


class ReservationCreateDialog(QDialog):
    def __init__(
        self,
        *,
        item_options: list[tuple[str, str]],
        storeroom_options: list[tuple[str, str]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Stock Reservation")
        self.resize(520, 500)
        self._setup_ui(item_options=item_options, storeroom_options=storeroom_options)

    def _setup_ui(
        self,
        *,
        item_options: list[tuple[str, str]],
        storeroom_options: list[tuple[str, str]],
    ) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Reserve available stock against a real upstream demand reference. The reservation reduces availability without reducing on-hand stock."
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
        self.quantity_spin.setMinimum(0.001)
        self.use_need_by_check = QCheckBox("Set need-by date")
        self.need_by_edit = QDateEdit()
        self.need_by_edit.setCalendarPopup(True)
        self.need_by_edit.setDate(QDate.currentDate())
        self.need_by_edit.setEnabled(False)
        self.source_type_edit = QLineEdit()
        self.source_type_edit.setPlaceholderText("work_order, task, work_request, project, ...")
        self.source_id_edit = QLineEdit()
        self.source_id_edit.setPlaceholderText("WO-100, TASK-42, ...")
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Reservation context, scope, or issuing notes.")

        form.addRow("Item", self.item_combo)
        form.addRow("Storeroom", self.storeroom_combo)
        form.addRow("Reserved Qty", self.quantity_spin)
        form.addRow("Need By", self.use_need_by_check)
        form.addRow("", self.need_by_edit)
        form.addRow("Source Type", self.source_type_edit)
        form.addRow("Source ID", self.source_id_edit)
        form.addRow("Notes", self.notes_edit)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.use_need_by_check.toggled.connect(self.need_by_edit.setEnabled)

    @property
    def stock_item_id(self) -> str:
        return str(self.item_combo.currentData() or "").strip()

    @property
    def storeroom_id(self) -> str:
        return str(self.storeroom_combo.currentData() or "").strip()

    @property
    def reserved_qty(self) -> float:
        return float(self.quantity_spin.value())

    @property
    def need_by_date(self) -> date | None:
        if not self.use_need_by_check.isChecked():
            return None
        return self.need_by_edit.date().toPython()

    @property
    def source_reference_type(self) -> str:
        return self.source_type_edit.text().strip()

    @property
    def source_reference_id(self) -> str:
        return self.source_id_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()


class ReservationIssueDialog(QDialog):
    def __init__(
        self,
        *,
        reservation_number: str,
        remaining_qty: float,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._remaining_qty = float(remaining_qty or 0.0)
        self.setWindowTitle(f"Issue Reservation - {reservation_number}")
        self.resize(460, 300)
        self._setup_ui(reservation_number=reservation_number)

    def _setup_ui(self, *, reservation_number: str) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Issue reserved stock against the held quantity. This reduces on-hand stock and consumes the reservation at the same time."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.reservation_label = QLabel(reservation_number)
        self.remaining_label = QLabel(f"{self._remaining_qty:,.3f}")
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setDecimals(3)
        self.quantity_spin.setMaximum(self._remaining_qty)
        self.quantity_spin.setMinimum(0.001)
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Issuing context or execution note.")

        form.addRow("Reservation", self.reservation_label)
        form.addRow("Remaining Qty", self.remaining_label)
        form.addRow("Issue Qty", self.quantity_spin)
        form.addRow("Notes", self.notes_edit)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @property
    def quantity(self) -> float:
        return float(self.quantity_spin.value())

    @property
    def note(self) -> str:
        return self.notes_edit.toPlainText().strip()


__all__ = ["ReservationCreateDialog", "ReservationIssueDialog"]
