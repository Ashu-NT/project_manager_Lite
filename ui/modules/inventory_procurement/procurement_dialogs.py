from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.platform.shared.styles.style_utils import style_table
from core.modules.inventory_procurement.domain import PurchaseOrder, PurchaseRequisition

_REQUISITION_PRIORITIES = ("LOW", "NORMAL", "HIGH", "URGENT")


def _set_combo_to_data(combo: QComboBox, value: str) -> None:
    index = combo.findData(value)
    if index >= 0:
        combo.setCurrentIndex(index)


def _set_optional_date(date_edit: QDateEdit, enabled_check: QCheckBox, value: date | None) -> None:
    if value is None:
        enabled_check.setChecked(False)
        return
    enabled_check.setChecked(True)
    date_edit.setDate(QDate(value.year, value.month, value.day))


class RequisitionEditDialog(QDialog):
    def __init__(
        self,
        *,
        site_options: list[tuple[str, str]],
        storeroom_options: list[tuple[str, str, str]],
        requisition: PurchaseRequisition | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._requisition = requisition
        self._storeroom_options = list(storeroom_options)
        self.setWindowTitle("Edit Purchase Requisition" if requisition is not None else "New Purchase Requisition")
        self.resize(520, 460)
        self._setup_ui(site_options=site_options)
        self._load_requisition()

    def _setup_ui(self, *, site_options: list[tuple[str, str]]) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Capture supply demand against a real site and storeroom first. Approval routing and sourcing stay in the shared workflow and procurement services."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.site_combo = QComboBox()
        for label, row_id in site_options:
            self.site_combo.addItem(label, row_id)
        self.storeroom_combo = QComboBox()
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(_REQUISITION_PRIORITIES)
        self.purpose_edit = QLineEdit()
        self.use_needed_by_check = QCheckBox("Set needed-by date")
        self.needed_by_edit = QDateEdit()
        self.needed_by_edit.setCalendarPopup(True)
        self.needed_by_edit.setDate(QDate.currentDate())
        self.needed_by_edit.setEnabled(False)
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Scope, urgency, or requester context.")

        form.addRow("Site", self.site_combo)
        form.addRow("Storeroom", self.storeroom_combo)
        form.addRow("Priority", self.priority_combo)
        form.addRow("Purpose", self.purpose_edit)
        needed_row = QHBoxLayout()
        needed_row.addWidget(self.use_needed_by_check)
        needed_row.addWidget(self.needed_by_edit, 1)
        form.addRow("Needed By", needed_row)
        form.addRow("Notes", self.notes_edit)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.site_combo.currentIndexChanged.connect(self._reload_storerooms)
        self.use_needed_by_check.toggled.connect(self.needed_by_edit.setEnabled)
        self._reload_storerooms()

    def _load_requisition(self) -> None:
        requisition = self._requisition
        if requisition is None:
            return
        _set_combo_to_data(self.site_combo, requisition.requesting_site_id)
        self._reload_storerooms()
        _set_combo_to_data(self.storeroom_combo, requisition.requesting_storeroom_id)
        self.priority_combo.setCurrentText(requisition.priority or "NORMAL")
        self.purpose_edit.setText(requisition.purpose)
        _set_optional_date(self.needed_by_edit, self.use_needed_by_check, requisition.needed_by_date)
        self.notes_edit.setPlainText(requisition.notes)

    def _reload_storerooms(self) -> None:
        site_id = self.site_id
        current_storeroom_id = self.storeroom_id
        self.storeroom_combo.blockSignals(True)
        self.storeroom_combo.clear()
        for label, storeroom_id, option_site_id in self._storeroom_options:
            if option_site_id == site_id:
                self.storeroom_combo.addItem(label, storeroom_id)
        _set_combo_to_data(self.storeroom_combo, current_storeroom_id)
        self.storeroom_combo.blockSignals(False)

    @property
    def site_id(self) -> str:
        return str(self.site_combo.currentData() or "").strip()

    @property
    def storeroom_id(self) -> str:
        return str(self.storeroom_combo.currentData() or "").strip()

    @property
    def priority(self) -> str:
        return str(self.priority_combo.currentText()).strip().upper()

    @property
    def purpose(self) -> str:
        return self.purpose_edit.text().strip()

    @property
    def needed_by_date(self) -> date | None:
        if not self.use_needed_by_check.isChecked():
            return None
        return self.needed_by_edit.date().toPython()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()


class RequisitionLineDialog(QDialog):
    def __init__(
        self,
        *,
        item_options: list[tuple[str, str]],
        supplier_options: list[tuple[str, str]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Requisition Line")
        self.resize(520, 500)
        self._setup_ui(item_options=item_options, supplier_options=supplier_options)

    def _setup_ui(
        self,
        *,
        item_options: list[tuple[str, str]],
        supplier_options: list[tuple[str, str]],
    ) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Capture the specific item demand line that the sourcing team will convert into procurement activity."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.item_combo = QComboBox()
        self.item_combo.addItems([])
        for label, row_id in item_options:
            self.item_combo.addItem(label, row_id)
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setDecimals(3)
        self.quantity_spin.setMaximum(999999999)
        self.quantity_spin.setMinimum(0.001)
        self.estimated_cost_spin = QDoubleSpinBox()
        self.estimated_cost_spin.setDecimals(4)
        self.estimated_cost_spin.setMaximum(999999999)
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("None", "")
        for label, row_id in supplier_options:
            self.supplier_combo.addItem(label, row_id)
        self.description_edit = QLineEdit()
        self.use_needed_by_check = QCheckBox("Set line needed-by date")
        self.needed_by_edit = QDateEdit()
        self.needed_by_edit.setCalendarPopup(True)
        self.needed_by_edit.setDate(QDate.currentDate())
        self.needed_by_edit.setEnabled(False)
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Line-specific buying notes or supplier context.")

        form.addRow("Item", self.item_combo)
        form.addRow("Quantity", self.quantity_spin)
        form.addRow("Estimated Cost", self.estimated_cost_spin)
        form.addRow("Suggested Supplier", self.supplier_combo)
        form.addRow("Description", self.description_edit)
        needed_row = QHBoxLayout()
        needed_row.addWidget(self.use_needed_by_check)
        needed_row.addWidget(self.needed_by_edit, 1)
        form.addRow("Needed By", needed_row)
        form.addRow("Notes", self.notes_edit)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.use_needed_by_check.toggled.connect(self.needed_by_edit.setEnabled)

    @property
    def stock_item_id(self) -> str:
        return str(self.item_combo.currentData() or "").strip()

    @property
    def quantity_requested(self) -> float:
        return float(self.quantity_spin.value())

    @property
    def estimated_unit_cost(self) -> float:
        return float(self.estimated_cost_spin.value())

    @property
    def suggested_supplier_party_id(self) -> str | None:
        value = str(self.supplier_combo.currentData() or "").strip()
        return value or None

    @property
    def description(self) -> str:
        return self.description_edit.text().strip()

    @property
    def needed_by_date(self) -> date | None:
        if not self.use_needed_by_check.isChecked():
            return None
        return self.needed_by_edit.date().toPython()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()


class PurchaseOrderEditDialog(QDialog):
    def __init__(
        self,
        *,
        site_options: list[tuple[str, str]],
        supplier_options: list[tuple[str, str]],
        requisition_options: list[tuple[str, str]],
        purchase_order: PurchaseOrder | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._purchase_order = purchase_order
        self.setWindowTitle("Edit Purchase Order" if purchase_order is not None else "New Purchase Order")
        self.resize(540, 520)
        self._setup_ui(
            site_options=site_options,
            supplier_options=supplier_options,
            requisition_options=requisition_options,
        )
        self._load_purchase_order()

    def _setup_ui(
        self,
        *,
        site_options: list[tuple[str, str]],
        supplier_options: list[tuple[str, str]],
        requisition_options: list[tuple[str, str]],
    ) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Purchase orders commit supply externally while still referencing shared sites and suppliers by platform identity."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.site_combo = QComboBox()
        for label, row_id in site_options:
            self.site_combo.addItem(label, row_id)
        self.supplier_combo = QComboBox()
        for label, row_id in supplier_options:
            self.supplier_combo.addItem(label, row_id)
        self.source_requisition_combo = QComboBox()
        self.source_requisition_combo.addItem("None", "")
        for label, row_id in requisition_options:
            self.source_requisition_combo.addItem(label, row_id)
        self.currency_code_edit = QLineEdit()
        self.currency_code_edit.setPlaceholderText("Defaults from site when left blank in later slices.")
        self.use_expected_delivery_check = QCheckBox("Set expected delivery date")
        self.expected_delivery_edit = QDateEdit()
        self.expected_delivery_edit.setCalendarPopup(True)
        self.expected_delivery_edit.setDate(QDate.currentDate())
        self.expected_delivery_edit.setEnabled(False)
        self.supplier_reference_edit = QLineEdit()
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Buying context, freight notes, or special handling instructions.")

        form.addRow("Site", self.site_combo)
        form.addRow("Supplier", self.supplier_combo)
        form.addRow("Source Requisition", self.source_requisition_combo)
        form.addRow("Currency", self.currency_code_edit)
        expected_row = QHBoxLayout()
        expected_row.addWidget(self.use_expected_delivery_check)
        expected_row.addWidget(self.expected_delivery_edit, 1)
        form.addRow("Expected Delivery", expected_row)
        form.addRow("Supplier Reference", self.supplier_reference_edit)
        form.addRow("Notes", self.notes_edit)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.use_expected_delivery_check.toggled.connect(self.expected_delivery_edit.setEnabled)

    def _load_purchase_order(self) -> None:
        purchase_order = self._purchase_order
        if purchase_order is None:
            return
        _set_combo_to_data(self.site_combo, purchase_order.site_id)
        _set_combo_to_data(self.supplier_combo, purchase_order.supplier_party_id)
        _set_combo_to_data(self.source_requisition_combo, purchase_order.source_requisition_id or "")
        self.currency_code_edit.setText(purchase_order.currency_code)
        _set_optional_date(
            self.expected_delivery_edit,
            self.use_expected_delivery_check,
            purchase_order.expected_delivery_date,
        )
        self.supplier_reference_edit.setText(purchase_order.supplier_reference)
        self.notes_edit.setPlainText(purchase_order.notes)

    @property
    def site_id(self) -> str:
        return str(self.site_combo.currentData() or "").strip()

    @property
    def supplier_party_id(self) -> str:
        return str(self.supplier_combo.currentData() or "").strip()

    @property
    def source_requisition_id(self) -> str | None:
        value = str(self.source_requisition_combo.currentData() or "").strip()
        return value or None

    @property
    def currency_code(self) -> str:
        return self.currency_code_edit.text().strip()

    @property
    def expected_delivery_date(self) -> date | None:
        if not self.use_expected_delivery_check.isChecked():
            return None
        return self.expected_delivery_edit.date().toPython()

    @property
    def supplier_reference(self) -> str:
        return self.supplier_reference_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()


class PurchaseOrderLineDialog(QDialog):
    def __init__(
        self,
        *,
        item_options: list[tuple[str, str]],
        storeroom_options: list[tuple[str, str]],
        requisition_line_options: list[tuple[str, str]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Purchase-Order Line")
        self.resize(540, 520)
        self._setup_ui(
            item_options=item_options,
            storeroom_options=storeroom_options,
            requisition_line_options=requisition_line_options,
        )

    def _setup_ui(
        self,
        *,
        item_options: list[tuple[str, str]],
        storeroom_options: list[tuple[str, str]],
        requisition_line_options: list[tuple[str, str]],
    ) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Create a committed buying line with the final receiving destination and, when relevant, a requisition-line source."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.item_combo = QComboBox()
        for label, row_id in item_options:
            self.item_combo.addItem(label, row_id)
        self.destination_storeroom_combo = QComboBox()
        for label, row_id in storeroom_options:
            self.destination_storeroom_combo.addItem(label, row_id)
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setDecimals(3)
        self.quantity_spin.setMaximum(999999999)
        self.quantity_spin.setMinimum(0.001)
        self.unit_price_spin = QDoubleSpinBox()
        self.unit_price_spin.setDecimals(4)
        self.unit_price_spin.setMaximum(999999999)
        self.source_requisition_line_combo = QComboBox()
        self.source_requisition_line_combo.addItem("None", "")
        for label, row_id in requisition_line_options:
            self.source_requisition_line_combo.addItem(label, row_id)
        self.use_expected_delivery_check = QCheckBox("Set line expected delivery date")
        self.expected_delivery_edit = QDateEdit()
        self.expected_delivery_edit.setCalendarPopup(True)
        self.expected_delivery_edit.setDate(QDate.currentDate())
        self.expected_delivery_edit.setEnabled(False)
        self.description_edit = QLineEdit()
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Receiving notes or line-level supplier remarks.")

        form.addRow("Item", self.item_combo)
        form.addRow("Destination Storeroom", self.destination_storeroom_combo)
        form.addRow("Quantity", self.quantity_spin)
        form.addRow("Unit Price", self.unit_price_spin)
        form.addRow("Source Requisition Line", self.source_requisition_line_combo)
        expected_row = QHBoxLayout()
        expected_row.addWidget(self.use_expected_delivery_check)
        expected_row.addWidget(self.expected_delivery_edit, 1)
        form.addRow("Expected Delivery", expected_row)
        form.addRow("Description", self.description_edit)
        form.addRow("Notes", self.notes_edit)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.use_expected_delivery_check.toggled.connect(self.expected_delivery_edit.setEnabled)

    @property
    def stock_item_id(self) -> str:
        return str(self.item_combo.currentData() or "").strip()

    @property
    def destination_storeroom_id(self) -> str:
        return str(self.destination_storeroom_combo.currentData() or "").strip()

    @property
    def quantity_ordered(self) -> float:
        return float(self.quantity_spin.value())

    @property
    def unit_price(self) -> float:
        return float(self.unit_price_spin.value())

    @property
    def source_requisition_line_id(self) -> str | None:
        value = str(self.source_requisition_line_combo.currentData() or "").strip()
        return value or None

    @property
    def expected_delivery_date(self) -> date | None:
        if not self.use_expected_delivery_check.isChecked():
            return None
        return self.expected_delivery_edit.date().toPython()

    @property
    def description(self) -> str:
        return self.description_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()


class ReceiptPostDialog(QDialog):
    def __init__(
        self,
        *,
        purchase_order_number: str,
        line_rows: list[dict[str, object]],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._line_rows = list(line_rows)
        self._accepted_spins: dict[str, QDoubleSpinBox] = {}
        self._rejected_spins: dict[str, QDoubleSpinBox] = {}
        self._cost_spins: dict[str, QDoubleSpinBox] = {}
        self.setWindowTitle(f"Post Receipt - {purchase_order_number}")
        self.resize(840, 560)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Post accepted and rejected receipt quantities against open purchase-order lines. Accepted quantities increase stock; rejected quantities close demand without increasing on-hand."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.delivery_reference_edit = QLineEdit()
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Receipt header notes, carrier remarks, or inspection summary.")
        form.addRow("Delivery Reference", self.delivery_reference_edit)
        form.addRow("Notes", self.notes_edit)
        root.addLayout(form)

        self.table = QTableWidget(len(self._line_rows), 7)
        self.table.setHorizontalHeaderLabels(
            ["Item", "Storeroom", "Outstanding", "UOM", "Accepted", "Rejected", "Unit Cost"]
        )
        style_table(self.table)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.verticalHeader().setVisible(False)
        for row_index, row in enumerate(self._line_rows):
            outstanding = float(row.get("outstanding_qty") or 0.0)
            uom = str(row.get("uom") or "")
            unit_cost = float(row.get("unit_price") or 0.0)
            purchase_order_line_id = str(row.get("purchase_order_line_id") or "")
            self.table.setItem(row_index, 0, QTableWidgetItem(str(row.get("item_label") or "-")))
            self.table.setItem(row_index, 1, QTableWidgetItem(str(row.get("storeroom_label") or "-")))
            self.table.setItem(row_index, 2, QTableWidgetItem(f"{outstanding:,.3f}"))
            self.table.setItem(row_index, 3, QTableWidgetItem(uom))

            accepted_spin = QDoubleSpinBox()
            accepted_spin.setDecimals(3)
            accepted_spin.setMaximum(max(outstanding, 0.0))
            accepted_spin.setAlignment(Qt.AlignRight)
            self.table.setCellWidget(row_index, 4, accepted_spin)
            self._accepted_spins[purchase_order_line_id] = accepted_spin

            rejected_spin = QDoubleSpinBox()
            rejected_spin.setDecimals(3)
            rejected_spin.setMaximum(max(outstanding, 0.0))
            rejected_spin.setAlignment(Qt.AlignRight)
            self.table.setCellWidget(row_index, 5, rejected_spin)
            self._rejected_spins[purchase_order_line_id] = rejected_spin

            cost_spin = QDoubleSpinBox()
            cost_spin.setDecimals(4)
            cost_spin.setMaximum(999999999)
            cost_spin.setAlignment(Qt.AlignRight)
            cost_spin.setValue(unit_cost)
            self.table.setCellWidget(row_index, 6, cost_spin)
            self._cost_spins[purchase_order_line_id] = cost_spin

        root.addWidget(self.table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @property
    def supplier_delivery_reference(self) -> str:
        return self.delivery_reference_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()

    @property
    def receipt_lines(self) -> list[dict[str, object]]:
        payload: list[dict[str, object]] = []
        for row in self._line_rows:
            purchase_order_line_id = str(row.get("purchase_order_line_id") or "")
            accepted = float(self._accepted_spins[purchase_order_line_id].value())
            rejected = float(self._rejected_spins[purchase_order_line_id].value())
            if accepted <= 0 and rejected <= 0:
                continue
            payload.append(
                {
                    "purchase_order_line_id": purchase_order_line_id,
                    "quantity_accepted": accepted,
                    "quantity_rejected": rejected,
                    "unit_cost": float(self._cost_spins[purchase_order_line_id].value()),
                }
            )
        return payload


__all__ = [
    "PurchaseOrderEditDialog",
    "PurchaseOrderLineDialog",
    "ReceiptPostDialog",
    "RequisitionEditDialog",
    "RequisitionLineDialog",
]
