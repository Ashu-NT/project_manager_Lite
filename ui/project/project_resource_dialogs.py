from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtWidgets

from core.exceptions import NotFoundError
from core.services.project import ProjectResourceService
from core.services.resource import ResourceService
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG, CurrencyType


class ProjectResourcesDialog(QtWidgets.QDialog):
    """
    Manage project-resource membership (planning layer).
    - Add existing master resources into a specific project.
    - Define project-specific hourly rate (override) and planned hours.
    """

    def __init__(
        self,
        project_id: str,
        resource_service: ResourceService,
        project_resource_service: ProjectResourceService,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Project Resources")
        self.resize(CFG.DEFAULT_PROJECT_WINDOW_SIZE)

        self._project_id = project_id
        self._resource_service = resource_service
        self._project_resource_service = project_resource_service

        self._table = QtWidgets.QTableWidget(0, 6)
        style_table(self._table)
        self._table.setHorizontalHeaderLabels(
            [
                "Resource",
                "Default Rate",
                "Project Rate",
                "Currency",
                "Planned Hours",
                "Active",
            ]
        )
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        hdr.setStretchLastSection(True)

        self._table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self._table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)

        self._btn_add = QtWidgets.QPushButton("Add")
        self._btn_edit = QtWidgets.QPushButton("Edit")
        self._btn_toggle = QtWidgets.QPushButton("Deactivate/Activate")
        self._btn_close = QtWidgets.QPushButton("Close")

        for btn in (
            self._btn_add,
            self._btn_edit,
            self._btn_toggle,
            self._btn_close,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addWidget(self._btn_add)
        btn_row.addWidget(self._btn_edit)
        btn_row.addWidget(self._btn_toggle)
        btn_row.addStretch(1)
        btn_row.addWidget(self._btn_close)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._table)
        layout.addLayout(btn_row)

        self._btn_add.clicked.connect(self._on_add)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_toggle.clicked.connect(self._on_toggle_active)
        self._btn_close.clicked.connect(self.accept)

        self.refresh()

    def refresh(self):
        rows = self._project_resource_service.list_by_project(self._project_id)

        valid = []
        for pr in rows:
            try:
                self._resource_service.get_resource(pr.resource_id)
                valid.append(pr)
            except NotFoundError:
                self._project_resource_service.delete(pr.id)

        rows = valid

        self._table.setRowCount(0)
        for pr in rows:
            try:
                res = self._resource_service.get_resource(pr.resource_id)
            except NotFoundError:
                res = None

            if not res:
                r = self._table.rowCount()
                self._table.insertRow(r)

                item_name = QtWidgets.QTableWidgetItem(
                    f"<missing resource> ({pr.resource_id})"
                )
                item_name.setData(QtCore.Qt.ItemDataRole.UserRole, pr.id)

                self._table.setItem(r, 0, item_name)
                self._table.setItem(r, 1, QtWidgets.QTableWidgetItem(""))
                self._table.setItem(
                    r,
                    2,
                    QtWidgets.QTableWidgetItem(
                        "" if pr.hourly_rate is None else f"{float(pr.hourly_rate):,.2f}"
                    ),
                )
                self._table.setItem(
                    r,
                    3,
                    QtWidgets.QTableWidgetItem((pr.currency_code or "").upper()),
                )
                self._table.setItem(
                    r,
                    4,
                    QtWidgets.QTableWidgetItem(f"{float(pr.planned_hours or 0.0):,.2f}"),
                )
                self._table.setItem(
                    r,
                    5,
                    QtWidgets.QTableWidgetItem(
                        "Yes" if getattr(pr, "is_active", True) else "No"
                    ),
                )
                continue

            r = self._table.rowCount()
            self._table.insertRow(r)

            item_name = QtWidgets.QTableWidgetItem(res.name)
            item_name.setData(QtCore.Qt.ItemDataRole.UserRole, pr.id)

            default_rate = getattr(res, "hourly_rate", None)
            default_cur = getattr(res, "currency_code", "") or ""

            item_def_rate = QtWidgets.QTableWidgetItem(
                "" if default_rate is None else f"{float(default_rate):,.2f}"
            )
            item_proj_rate = QtWidgets.QTableWidgetItem(
                "" if pr.hourly_rate is None else f"{float(pr.hourly_rate):,.2f}"
            )

            cur = (pr.currency_code or default_cur or "").upper()
            item_cur = QtWidgets.QTableWidgetItem(cur)

            item_hours = QtWidgets.QTableWidgetItem(f"{float(pr.planned_hours or 0.0):,.2f}")
            item_active = QtWidgets.QTableWidgetItem(
                "Yes" if getattr(pr, "is_active", True) else "No"
            )

            self._table.setItem(r, 0, item_name)
            self._table.setItem(r, 1, item_def_rate)
            self._table.setItem(r, 2, item_proj_rate)
            self._table.setItem(r, 3, item_cur)
            self._table.setItem(r, 4, item_hours)
            self._table.setItem(r, 5, item_active)

    def _selected_project_resource_id(self) -> Optional[str]:
        sel = self._table.selectionModel().selectedRows()
        if not sel:
            return None
        row = sel[0].row()
        item = self._table.item(row, 0)
        return item.data(QtCore.Qt.ItemDataRole.UserRole) if item else None

    def _on_add(self):
        dlg = ProjectResourceEditDialog(
            project_id=self._project_id,
            resource_service=self._resource_service,
            project_resource_service=self._project_resource_service,
            project_resource_id=None,
            parent=self,
        )
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_edit(self):
        pr_id = self._selected_project_resource_id()
        if not pr_id:
            QtWidgets.QMessageBox.information(self, "Edit", "Please select a row to edit.")
            return
        dlg = ProjectResourceEditDialog(
            project_id=self._project_id,
            resource_service=self._resource_service,
            project_resource_service=self._project_resource_service,
            project_resource_id=pr_id,
            parent=self,
        )
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_toggle_active(self):
        pr_id = self._selected_project_resource_id()
        if not pr_id:
            QtWidgets.QMessageBox.information(self, "Status", "Please select a row.")
            return

        pr = self._project_resource_service.get(pr_id)
        if not pr:
            QtWidgets.QMessageBox.warning(self, "Status", "Selected item no longer exists.")
            self.refresh()
            return

        new_active = not bool(getattr(pr, "is_active", True))
        self._project_resource_service.set_active(pr_id, new_active)
        self.refresh()


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


__all__ = ["ProjectResourcesDialog", "ProjectResourceEditDialog"]
