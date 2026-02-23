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
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from core.models import Project, ProjectStatus
from ui.styles.ui_config import UIConfig as CFG, CurrencyType


class ProjectEditDialog(QDialog):
    def __init__(self, parent=None, project: Project | None = None):
        super().__init__(parent)
        self.setWindowTitle("Project" + (" - Edit" if project else " - New"))
        self._project = project

        self.name_edit = QLineEdit()
        self.client_edit = QLineEdit()
        self.client_contact_edit = QLineEdit()

        for edit in (
            self.name_edit,
            self.client_edit,
            self.client_contact_edit,
        ):
            edit.setSizePolicy(CFG.INPUT_POLICY)
            edit.setFixedHeight(CFG.INPUT_HEIGHT)
            edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)

        self.budget_spin = QDoubleSpinBox()
        self.budget_spin.setSizePolicy(CFG.INPUT_POLICY)
        self.budget_spin.setFixedHeight(CFG.INPUT_HEIGHT)
        self.budget_spin.setMinimum(CFG.MONEY_MIN)
        self.budget_spin.setMaximum(CFG.MONEY_MAX)
        self.budget_spin.setDecimals(CFG.MONEY_DECIMALS)
        self.budget_spin.setSingleStep(CFG.MONEY_STEP)
        self.budget_spin.setAlignment(CFG.ALIGN_RIGHT)

        self.currency_combo = QComboBox()
        self.currency_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.currency_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.currency_combo.setEditable(CFG.COMBO_EDITABLE)
        self.currency_combo.setMaxVisibleItems(CFG.COMBO_MAX_VISIBLE)

        for cur in CurrencyType:
            self.currency_combo.addItem(cur.value)
        self.currency_combo.setEditable(True)

        self.status_combo = QComboBox()
        self.status_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.status_combo.setFixedHeight(CFG.INPUT_HEIGHT)

        self._status_values: list[ProjectStatus] = [
            ProjectStatus.PLANNED,
            ProjectStatus.ACTIVE,
            ProjectStatus.ON_HOLD,
            ProjectStatus.COMPLETED,
        ]
        for status in self._status_values:
            self.status_combo.addItem(status.value)

        self.start_date_edit = QDateEdit()
        self.end_date_edit = QDateEdit()
        for date_edit in (self.start_date_edit, self.end_date_edit):
            date_edit.setSizePolicy(CFG.INPUT_POLICY)
            date_edit.setFixedHeight(CFG.INPUT_HEIGHT)
            date_edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)
            date_edit.setCalendarPopup(True)
            date_edit.setDisplayFormat(CFG.DATE_FORMAT)

        self.desc_edit = QTextEdit()
        self.desc_edit.setSizePolicy(CFG.TEXTEDIT_POLICY)
        self.desc_edit.setMinimumHeight(CFG.TEXTEDIT_MIN_HEIGHT)

        if project:
            self.name_edit.setText(project.name)
            self.client_edit.setText(project.client_name or "")
            self.client_contact_edit.setText(project.client_contact or "")

            if project.planned_budget is not None:
                self.budget_spin.setValue(project.planned_budget)

            if project.currency:
                idx = self.currency_combo.findText(project.currency)
                if idx >= 0:
                    self.currency_combo.setCurrentIndex(idx)
                else:
                    self.currency_combo.addItem(project.currency)
                    self.currency_combo.setCurrentIndex(self.currency_combo.count() - 1)

            if project.status:
                for i, status in enumerate(self._status_values):
                    if status == project.status:
                        self.status_combo.setCurrentIndex(i)
                        break

            if project.start_date:
                self.start_date_edit.setDate(project.start_date)
            else:
                self.start_date_edit.clear()
            if project.end_date:
                self.end_date_edit.setDate(project.end_date)
            else:
                self.end_date_edit.clear()

            self.desc_edit.setPlainText(project.description or "")
        else:
            today = QDate.currentDate()
            self.start_date_edit.setDate(today)
            self.end_date_edit.setDate(today)
            self.status_combo.setCurrentIndex(0)
            idx = self.currency_combo.findText(CFG.DEFAULT_CURRENCY_CODE)
            if idx >= 0:
                self.currency_combo.setCurrentIndex(idx)
            else:
                self.currency_combo.setCurrentText(CFG.DEFAULT_CURRENCY_CODE)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)

        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.DontWrapRows)

        form.addRow("Name:", self.name_edit)
        form.addRow("Client Name:", self.client_edit)
        form.addRow("Client Contact:", self.client_contact_edit)
        form.addRow("Planned Budget:", self.budget_spin)
        form.addRow("Currency:", self.currency_combo)
        form.addRow("Status:", self.status_combo)
        form.addRow("Start Date:", self.start_date_edit)
        form.addRow("End Date:", self.end_date_edit)
        form.addRow("Description:", self.desc_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.setCenterButtons(False)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_LG)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )

        layout.addLayout(form)
        layout.addWidget(buttons)

        self.setMinimumSize(self.sizeHint())

    @property
    def name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def description(self) -> str:
        return self.desc_edit.toPlainText().strip()

    @property
    def client_name(self) -> str:
        return self.client_edit.text().strip()

    @property
    def client_contact(self) -> str:
        return self.client_contact_edit.text().strip()

    @property
    def planned_budget(self) -> float | None:
        val = self.budget_spin.value()
        return val if val > 0.0 else None

    @property
    def currency(self) -> str | None:
        cur = self.currency_combo.currentText().strip()
        return cur if cur else None

    @property
    def status(self) -> ProjectStatus:
        idx = self.status_combo.currentIndex()
        if 0 <= idx < len(self._status_values):
            return self._status_values[idx]
        return ProjectStatus.PLANNED

    @property
    def start_date(self) -> Optional[date]:
        if self.start_date_edit.date().isValid():
            qdate = self.start_date_edit.date()
            return date(qdate.year(), qdate.month(), qdate.day())
        return None

    @property
    def end_date(self) -> Optional[date]:
        if self.end_date_edit.date().isValid():
            qdate = self.end_date_edit.date()
            return date(qdate.year(), qdate.month(), qdate.day())
        return None


__all__ = ["ProjectEditDialog"]
