from __future__ import annotations

from typing import Optional

from PySide6 import QtWidgets

from core.exceptions import NotFoundError
from core.services.project import ProjectResourceService
from core.services.resource import ResourceService
from ui.styles.ui_config import UIConfig as CFG, CurrencyType


class ProjectResourceEditDialog(QtWidgets.QDialog):
    """Add/edit one project-resource row."""

    def __init__(
        self,
        project_id: str,
        resource_service: ResourceService,
        project_resource_service: ProjectResourceService,
        project_resource_id: Optional[str],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(
            "Add Project Resource" if not project_resource_id else "Edit Project Resource"
        )
        self.resize(520, 220)

        self._project_id = project_id
        self._resource_service = resource_service
        self._project_resource_service = project_resource_service
        self._pr_id = project_resource_id

        self._cmb_resource = QtWidgets.QComboBox()
        self._cmb_resource.setSizePolicy(CFG.INPUT_POLICY)
        self._cmb_resource.setFixedHeight(CFG.INPUT_HEIGHT)

        self._spn_rate = QtWidgets.QDoubleSpinBox()
        self._spn_rate.setSizePolicy(CFG.INPUT_POLICY)
        self._spn_rate.setFixedHeight(CFG.INPUT_HEIGHT)
        self._spn_rate.setDecimals(CFG.MONEY_DECIMALS)
        self._spn_rate.setSingleStep(CFG.MONEY_STEP)
        self._spn_rate.setMinimum(0.0)
        self._spn_rate.setMaximum(CFG.MONEY_MAX)
        self._spn_rate.setAlignment(CFG.ALIGN_RIGHT)

        self._cmb_currency = QtWidgets.QComboBox()
        self._cmb_currency.setSizePolicy(CFG.INPUT_POLICY)
        self._cmb_currency.setFixedHeight(CFG.INPUT_HEIGHT)
        self._cmb_currency.setEditable(True)
        self._cmb_currency.setMaxVisibleItems(CFG.COMBO_MAX_VISIBLE)
        for cur in CurrencyType:
            self._cmb_currency.addItem(cur.value)

        self._spn_planned_hours = QtWidgets.QDoubleSpinBox()
        self._spn_planned_hours.setSizePolicy(CFG.INPUT_POLICY)
        self._spn_planned_hours.setFixedHeight(CFG.INPUT_HEIGHT)
        self._spn_planned_hours.setDecimals(2)
        self._spn_planned_hours.setSingleStep(1.0)
        self._spn_planned_hours.setMinimum(0.0)
        self._spn_planned_hours.setMaximum(1000000.0)
        self._spn_planned_hours.setAlignment(CFG.ALIGN_RIGHT)

        self._spn_rate.setSpecialValueText("Use resource default")
        self._spn_rate.setValue(0.0)
        self._rate_touched = False
        self._spn_rate.valueChanged.connect(lambda _v: setattr(self, "_rate_touched", True))

        self._currency_touched = False
        self._cmb_currency.currentTextChanged.connect(
            lambda _t: setattr(self, "_currency_touched", True)
        )

        self._chk_active = QtWidgets.QCheckBox("Active")

        btn_save = QtWidgets.QPushButton("Save")
        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_save.clicked.connect(self._on_save)
        btn_cancel.clicked.connect(self.reject)

        form = QtWidgets.QFormLayout()
        form.addRow("Resource", self._cmb_resource)
        form.addRow("Project hourly rate", self._spn_rate)
        form.addRow("Currency", self._cmb_currency)
        form.addRow("Planned hours", self._spn_planned_hours)
        form.addRow("", self._chk_active)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(btn_save)
        btns.addWidget(btn_cancel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addStretch(1)
        layout.addLayout(btns)

        self._load()

    def _load(self):
        resources = [
            r for r in self._resource_service.list_resources() if getattr(r, "is_active", True)
        ]

        self._cmb_resource.clear()
        for resource in resources:
            self._cmb_resource.addItem(resource.name, resource.id)

        self._cmb_resource.currentIndexChanged.connect(self._apply_resource_defaults)

        if self._pr_id:
            pr = self._project_resource_service.get(self._pr_id)
            if not pr:
                QtWidgets.QMessageBox.warning(self, "Edit", "Item not found.")
                self.reject()
                return

            idx = self._cmb_resource.findData(pr.resource_id)
            if idx >= 0:
                self._cmb_resource.setCurrentIndex(idx)
            self._cmb_resource.setEnabled(False)

            if pr.hourly_rate is None:
                self._spn_rate.setValue(0.0)
                self._rate_touched = False
            else:
                self._spn_rate.setValue(float(pr.hourly_rate))
                self._rate_touched = True

            cur = (pr.currency_code or "").upper()
            idx = self._cmb_currency.findText(cur)
            if idx >= 0:
                self._cmb_currency.setCurrentIndex(idx)
            else:
                if cur:
                    self._cmb_currency.addItem(cur)
                    self._cmb_currency.setCurrentIndex(self._cmb_currency.count() - 1)
            self._currency_touched = bool(cur)

            self._spn_planned_hours.setValue(float(pr.planned_hours or 0.0))
            self._chk_active.setChecked(bool(getattr(pr, "is_active", True)))
        else:
            self._chk_active.setChecked(True)

    def _apply_resource_defaults(self):
        rid = self._cmb_resource.currentData()
        if not rid:
            return
        try:
            res = self._resource_service.get_resource(rid)
        except NotFoundError:
            return

        if not getattr(self, "_rate_touched", False):
            self._spn_rate.setValue(0.0)

        if not getattr(self, "_currency_touched", False):
            default_cur = (getattr(res, "currency_code", "") or "").upper()
            idx = self._cmb_currency.findText(default_cur)
            if idx >= 0:
                self._cmb_currency.setCurrentIndex(idx)
            else:
                if default_cur:
                    self._cmb_currency.addItem(default_cur)
                    self._cmb_currency.setCurrentIndex(self._cmb_currency.count() - 1)

    def _on_save(self):
        resource_id = self._cmb_resource.currentData()
        if not resource_id:
            QtWidgets.QMessageBox.warning(self, "Save", "Please select a resource.")
            return

        try:
            res = self._resource_service.get_resource(resource_id)
        except NotFoundError as exc:
            QtWidgets.QMessageBox.warning(self, "Save", str(exc))
            return

        if getattr(self, "_rate_touched", False) and self._spn_rate.value() > 0:
            rate = float(self._spn_rate.value())
        else:
            default_rate = getattr(res, "hourly_rate", None)
            rate = float(default_rate) if default_rate is not None else None

        cur_txt = (self._cmb_currency.currentText() or "").strip().upper()
        if getattr(self, "_currency_touched", False) and cur_txt:
            cur = cur_txt
        else:
            cur = (getattr(res, "currency_code", None) or "")
            cur = cur.upper() if cur else None

        planned_hours = float(self._spn_planned_hours.value() or 0.0)
        active = self._chk_active.isChecked()

        try:
            if self._pr_id:
                self._project_resource_service.update(
                    pr_id=self._pr_id,
                    hourly_rate=rate,
                    currency_code=cur,
                    planned_hours=planned_hours,
                    is_active=active,
                )
            else:
                self._project_resource_service.add_to_project(
                    project_id=self._project_id,
                    resource_id=resource_id,
                    hourly_rate=rate,
                    currency_code=cur,
                    planned_hours=planned_hours,
                    is_active=active,
                )
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Save failed", str(exc))
            return

        self.accept()


__all__ = ["ProjectResourceEditDialog"]
