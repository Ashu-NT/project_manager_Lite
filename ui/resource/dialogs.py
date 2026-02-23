from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from core.models import CostType, Resource
from ui.styles.ui_config import UIConfig as CFG, CurrencyType


class ResourceEditDialog(QDialog):
    def __init__(self, parent=None, resource: Resource | None = None):
        super().__init__(parent)
        self.setWindowTitle("Resource" + (" - Edit" if resource else " - New"))
        self._resource: Resource | None = resource

        self.name_edit = QLineEdit()
        self.role_edit = QLineEdit()
        for edit in (self.name_edit, self.role_edit):
            edit.setSizePolicy(CFG.INPUT_POLICY)
            edit.setFixedHeight(CFG.INPUT_HEIGHT)
            edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)

        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setSizePolicy(CFG.INPUT_POLICY)
        self.rate_spin.setFixedHeight(CFG.INPUT_HEIGHT)
        self.rate_spin.setMinimum(CFG.MONEY_MIN)
        self.rate_spin.setMaximum(CFG.MONEY_MAX)
        self.rate_spin.setDecimals(CFG.MONEY_DECIMALS)
        self.rate_spin.setSingleStep(CFG.MONEY_STEP)
        self.rate_spin.setAlignment(CFG.ALIGN_RIGHT)

        self.category_combo = QComboBox()
        self._cost_types: list[CostType] = [
            CostType.LABOR,
            CostType.MATERIAL,
            CostType.OVERHEAD,
            CostType.EQUIPMENT,
            CostType.CONTINGENCY,
            CostType.SUBCONTRACT,
            CostType.OTHER,
        ]
        for ct in self._cost_types:
            self.category_combo.addItem(ct.value, userData=ct)
        self.category_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.category_combo.setFixedHeight(CFG.INPUT_HEIGHT)

        self.currency_combo = QComboBox()
        self.currency_combo.setEditable(True)
        for cur in CurrencyType:
            self.currency_combo.addItem(cur.value)
        self.currency_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.currency_combo.setFixedHeight(CFG.INPUT_HEIGHT)

        self.active_check = QCheckBox("Active")
        self.active_check.setSizePolicy(CFG.CHKBOX_FIXED_HEIGHT)

        if resource:
            self.name_edit.setText(resource.name)
            self.role_edit.setText(resource.role or "")
            if resource.hourly_rate is not None:
                self.rate_spin.setValue(resource.hourly_rate)
            for i, ct in enumerate(self._cost_types):
                if ct == getattr(resource, "cost_type", CostType.LABOR):
                    self.category_combo.setCurrentIndex(i)
                    break
            if getattr(resource, "currency_code", None):
                self.currency_combo.setCurrentText(resource.currency_code)
            self.active_check.setChecked(getattr(resource, "is_active", True))
        else:
            self.currency_combo.setCurrentText(CFG.DEFAULT_CURRENCY_CODE)
            self.active_check.setChecked(True)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.DontWrapRows)
        form.addRow("Name:", self.name_edit)
        form.addRow("Role:", self.role_edit)
        form.addRow("Category:", self.category_combo)
        form.addRow("Hourly rate:", self.rate_spin)
        form.addRow("Currency:", self.currency_combo)
        form.addRow("", self.active_check)

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
    def role(self) -> str:
        return self.role_edit.text().strip()

    @property
    def hourly_rate(self) -> float:
        return self.rate_spin.value()

    @property
    def is_active(self) -> bool:
        return self.active_check.isChecked()

    @property
    def cost_type(self) -> CostType:
        idx = self.category_combo.currentIndex()
        if 0 <= idx < len(self._cost_types):
            return self._cost_types[idx]
        return CostType.LABOR

    @property
    def currency_code(self) -> str | None:
        txt = self.currency_combo.currentText().strip()
        return txt if txt else None


__all__ = ["ResourceEditDialog"]
