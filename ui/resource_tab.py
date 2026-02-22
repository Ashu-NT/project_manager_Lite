# ui/resource_tab.py
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
    QTableView, QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QCheckBox, QDialogButtonBox, QMessageBox
)

from core.services.resource_service import ResourceService
from core.exceptions import ValidationError, BusinessRuleError, NotFoundError
from core.models import Resource, CostType
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG, CurrencyType


class ResourceTableModel(QAbstractTableModel):
    HEADERS = ["Name", "Role", "Category", "Hourly rate", "Currency", "Active"]

    def __init__(self, resources: list[Resource] | None = None, parent=None):
        super().__init__(parent)
        self._resources: list[Resource] = resources or []

    def set_resources(self, resources: list[Resource]):
        self.beginResetModel()
        self._resources = resources
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._resources)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        r = self._resources[index.row()]
        col = index.column()
        if col == 0:
            return r.name
        elif col == 1:
            return r.role or ""
        elif col == 2:
            # Category
            return getattr(r, "cost_type", None).value if getattr(r, "cost_type", None) else ""
        elif col == 3:
            return f"{(r.hourly_rate or 0.0):.2f}"
        elif col == 4:
            return r.currency_code or ""
        elif col == 5:
            return "Yes" if getattr(r, "is_active", True) else "No"
        return None

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return super().headerData(section, orientation, role)

    def get_resource(self, row: int) -> Optional[Resource]:
        if 0 <= row < len(self._resources):
            return self._resources[row]
        return None
    
class ResourceEditDialog(QDialog):
    def __init__(self, parent=None, resource: Resource | None = None):
        super().__init__(parent)
        self.setWindowTitle("Resource" + (" - Edit" if resource else " - New"))
        self._resource = resource

        self.name_edit = QLineEdit()
        self.role_edit = QLineEdit()
        for edit in (
            self.name_edit,
            self.role_edit,
            ):
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

        # Category (cost type) combo
        self.category_combo = QComboBox()
        self._cost_types = [
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

        # Currency combo (editable)
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
            # set cost type
            for i, ct in enumerate(self._cost_types):
                if ct == getattr(resource, "cost_type", CostType.LABOR):
                    self.category_combo.setCurrentIndex(i)
                    break
            # set currency
            if getattr(resource, "currency_code", None):
                self.currency_combo.setCurrentText(resource.currency_code)
            self.active_check.setChecked(getattr(resource, "is_active", True))
        else:
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
        


        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_new = QPushButton(CFG.NEW_RESOURCE_LABEL)
        self.btn_edit = QPushButton(CFG.EDIT_LABEL)
        self.btn_delete = QPushButton(CFG.DELETE_LABEL)
        self.btn_toggle_active = QPushButton(CFG.TOGGLE_ACTIVE_LABEL)
       
        self.btn_reload_resources = QPushButton(CFG.REFRESH_RESOURCES_LABEL)
        
        for btn in(
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

        # Table
        self.table = QTableView()
        self.model = ResourceTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        style_table(self.table)
        layout.addWidget(self.table)

        # Signals
        self.btn_reload_resources.clicked.connect(self.reload_resources)
        self.btn_new.clicked.connect(self.create_resource)
        self.btn_edit.clicked.connect(self.edit_resource)
        self.btn_delete.clicked.connect(self.delete_resource)
        self.btn_toggle_active.clicked.connect(self.toggle_active)

    # -------- helpers -------- #

    def reload_resources(self):
        resources = self._resource_service.list_resources()
        self.model.set_resources(resources)


    def _get_selected_resource(self) -> Optional[Resource]:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        return self.model.get_resource(row)

    # -------- actions -------- #

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

