from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QHeaderView,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.models import Resource
from core.services.resource import ResourceService
from ui.resource.dialogs import ResourceEditDialog
from ui.resource.models import ResourceTableModel
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class ResourceTab(QWidget):
    def __init__(
        self,
        resource_service: ResourceService,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._resource_service = resource_service

        self._setup_ui()
        self.reload_resources()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )

        toolbar = QHBoxLayout()
        self.btn_new = QPushButton(CFG.NEW_RESOURCE_LABEL)
        self.btn_edit = QPushButton(CFG.EDIT_LABEL)
        self.btn_delete = QPushButton(CFG.DELETE_LABEL)
        self.btn_toggle_active = QPushButton(CFG.TOGGLE_ACTIVE_LABEL)
        self.btn_reload_resources = QPushButton(CFG.REFRESH_RESOURCES_LABEL)

        for btn in (
            self.btn_new,
            self.btn_edit,
            self.btn_delete,
            self.btn_toggle_active,
            self.btn_reload_resources,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)

        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_toggle_active)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_reload_resources)
        layout.addLayout(toolbar)

        self.table = QTableView()
        self.model = ResourceTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        style_table(self.table)
        hh = self.table.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Interactive)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hh.resizeSection(1, 180)
        layout.addWidget(self.table)

        self.btn_reload_resources.clicked.connect(self.reload_resources)
        self.btn_new.clicked.connect(self.create_resource)
        self.btn_edit.clicked.connect(self.edit_resource)
        self.btn_delete.clicked.connect(self.delete_resource)
        self.btn_toggle_active.clicked.connect(self.toggle_active)

    def reload_resources(self):
        resources = self._resource_service.list_resources()
        self.model.set_resources(resources)

    def _get_selected_resource(self) -> Optional[Resource]:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        return self.model.get_resource(row)

    def create_resource(self):
        dlg = ResourceEditDialog(self, resource=None)
        if dlg.exec() == QDialog.Accepted:
            try:
                self._resource_service.create_resource(
                    name=dlg.name,
                    role=dlg.role,
                    hourly_rate=dlg.hourly_rate,
                    is_active=dlg.is_active,
                    cost_type=dlg.cost_type,
                    currency_code=dlg.currency_code,
                )
            except ValidationError as e:
                QMessageBox.warning(self, "Validation error", str(e))
                return
            self.reload_resources()

    def edit_resource(self):
        r = self._get_selected_resource()
        if not r:
            QMessageBox.information(self, "Edit resource", "Please select a resource.")
            return
        dlg = ResourceEditDialog(self, resource=r)
        if dlg.exec() == QDialog.Accepted:
            try:
                self._resource_service.update_resource(
                    resource_id=r.id,
                    name=dlg.name,
                    role=dlg.role,
                    hourly_rate=dlg.hourly_rate,
                    is_active=dlg.is_active,
                    cost_type=dlg.cost_type,
                    currency_code=dlg.currency_code,
                )
            except (ValidationError, NotFoundError, BusinessRuleError) as e:
                QMessageBox.warning(self, "Error", str(e))
                return
            self.reload_resources()

    def delete_resource(self):
        r = self._get_selected_resource()
        if not r:
            QMessageBox.information(self, "Delete resource", "Please select a resource.")
            return
        confirm = QMessageBox.question(
            self,
            "Delete resource",
            f"Delete resource '{r.name}'? (Assignments may fail if still referenced.)",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self._resource_service.delete_resource(r.id)
        except BusinessRuleError as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        self.reload_resources()

    def toggle_active(self):
        r = self._get_selected_resource()
        if not r:
            QMessageBox.information(self, "Toggle active", "Please select a resource.")
            return
        try:
            self._resource_service.update_resource(
                resource_id=r.id,
                is_active=not getattr(r, "is_active", True),
            )
        except (ValidationError, NotFoundError, BusinessRuleError) as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        self.reload_resources()
