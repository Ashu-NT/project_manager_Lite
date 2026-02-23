from __future__ import annotations

from datetime import date
from typing import Optional

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QTextEdit,
    QVBoxLayout,
)

from core.models import CostItem, CostType, Project, Task
from ui.styles.ui_config import UIConfig as CFG, CurrencyType


class CostEditDialog(QDialog):
    def __init__(
        self,
        parent=None,
        project: Project | None = None,
        tasks: list[Task] | None = None,
        cost_item: CostItem | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Cost item" + (" - Edit" if cost_item else " - New"))
        self._project: Project | None = project
        self._tasks: list[Task] = tasks or []
        self._cost_item: CostItem | None = cost_item

        self.desc_edit = QTextEdit()
        self.desc_edit.setSizePolicy(CFG.TEXTEDIT_POLICY)
        self.desc_edit.setMinimumHeight(CFG.TEXTEDIT_MIN_HEIGHT)

        self.planned_spin = QDoubleSpinBox()
        self.actual_spin = QDoubleSpinBox()
        self.committed_spin = QDoubleSpinBox()
        for spin in (self.planned_spin, self.actual_spin, self.committed_spin):
            spin.setSizePolicy(CFG.INPUT_POLICY)
            spin.setFixedHeight(CFG.INPUT_HEIGHT)
            spin.setDecimals(CFG.MONEY_DECIMALS)
            spin.setSingleStep(CFG.MONEY_STEP)
            spin.setMinimum(CFG.MONEY_MIN)
            spin.setMaximum(CFG.MONEY_MAX)
            spin.setAlignment(CFG.ALIGN_RIGHT)

        self.task_combo = QComboBox()
        self.type_combo = QComboBox()
        for combo in (self.task_combo, self.type_combo):
            combo.setSizePolicy(CFG.INPUT_POLICY)
            combo.setFixedHeight(CFG.INPUT_HEIGHT)
            combo.setEditable(CFG.COMBO_EDITABLE)
            combo.setMaxVisibleItems(CFG.COMBO_MAX_VISIBLE)

        self.currency_combo = QComboBox()
        self.currency_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.currency_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.currency_combo.setEditable(CFG.COMBO_EDITABLE)
        self.currency_combo.setMaxVisibleItems(CFG.COMBO_MAX_VISIBLE)

        self.incurred_date = QDateEdit()
        self.incurred_date.setSizePolicy(CFG.INPUT_POLICY)
        self.incurred_date.setFixedHeight(CFG.INPUT_HEIGHT)
        self.incurred_date.setMinimumWidth(CFG.INPUT_MIN_WIDTH)
        self.incurred_date.setDate(QDate.currentDate())
        self.incurred_date.setCalendarPopup(True)
        self.incurred_date.setDisplayFormat(CFG.DATE_FORMAT)

        for cur in CurrencyType:
            self.currency_combo.addItem(cur.value)

        self.task_combo.addItem("(none)", userData=None)

        for cost_type in CostType:
            if cost_type == CostType.LABOR:
                continue
            self.type_combo.addItem(cost_type.value, userData=cost_type)

        for task in self._tasks:
            self.task_combo.addItem(task.name, userData=task.id)

        if cost_item:
            self.desc_edit.setPlainText(cost_item.description or "")
            if cost_item.planned_amount is not None:
                self.planned_spin.setValue(cost_item.planned_amount)
            if cost_item.actual_amount is not None:
                self.actual_spin.setValue(cost_item.actual_amount)
            if cost_item.task_id:
                for i in range(1, self.task_combo.count()):
                    if self.task_combo.itemData(i) == cost_item.task_id:
                        self.task_combo.setCurrentIndex(i)
                        break
            if cost_item.cost_type is not None:
                for i in range(self.type_combo.count()):
                    if self.type_combo.itemData(i) == cost_item.cost_type:
                        self.type_combo.setCurrentIndex(i)
                        break
            if getattr(cost_item, "currency_code", None):
                self.currency_combo.setCurrentText(str(cost_item.currency_code).upper())
            elif getattr(self._project, "currency", None):
                self.currency_combo.setCurrentText(str(self._project.currency).upper())
            else:
                self.currency_combo.setCurrentText(CFG.DEFAULT_CURRENCY_CODE)
        else:
            if getattr(self._project, "currency", None):
                self.currency_combo.setCurrentText(str(self._project.currency).upper())
            else:
                self.currency_combo.setCurrentText(CFG.DEFAULT_CURRENCY_CODE)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.DontWrapRows)
        form.addRow("Task:", self.task_combo)
        form.addRow("Planned amount:", self.planned_spin)
        form.addRow("Actual amount:", self.actual_spin)
        form.addRow("Committed Amount:", self.committed_spin)
        form.addRow("Type:", self.type_combo)
        form.addRow("Incurred date:", self.incurred_date)
        form.addRow("Currency (Optional):", self.currency_combo)
        form.addRow("Description:", self.desc_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.setCenterButtons(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_LG)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        layout.addLayout(form)
        layout.addWidget(buttons)

    @property
    def description(self) -> str:
        return self.desc_edit.toPlainText().strip()

    @property
    def task_id(self) -> Optional[str]:
        idx = self.task_combo.currentIndex()
        if idx < 0:
            return None
        return self.task_combo.itemData(idx)

    @property
    def planned_amount(self) -> float:
        return self.planned_spin.value()

    @property
    def actual_amount(self) -> Optional[float]:
        return self.actual_spin.value()

    @property
    def cost_type(self) -> CostType:
        idx = self.type_combo.currentIndex()
        return self.type_combo.itemData(idx) or CostType.OVERHEAD

    @property
    def committed_amount(self) -> float:
        return self.committed_spin.value()

    @property
    def incurred_date_value(self) -> date | None:
        if not self.incurred_date.date().isValid():
            return None
        qd = self.incurred_date.date()
        return date(qd.year(), qd.month(), qd.day())

    @property
    def currency_code(self) -> str | None:
        code = self.currency_combo.currentText().strip()
        return code or None


__all__ = ["CostEditDialog"]
