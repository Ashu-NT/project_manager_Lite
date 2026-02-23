from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtWidgets

from core.exceptions import NotFoundError
from core.services.project import ProjectResourceService
from core.services.resource import ResourceService
from ui.project.project_resource_edit_dialog import ProjectResourceEditDialog
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


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


__all__ = ["ProjectResourcesDialog"]
