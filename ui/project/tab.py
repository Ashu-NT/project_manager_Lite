# ui/project_tab.py
from __future__ import annotations
from datetime import date
from typing import Optional

from PySide6 import QtWidgets, QtCore
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableView,
    QDialog, QLineEdit, QTextEdit, QFormLayout, QDialogButtonBox,
    QMessageBox, QDoubleSpinBox, QDateEdit,QComboBox
)

from core.services.project import ProjectService
from core.services.task import TaskService
from core.services.reporting import ReportingService
from core.services.project import ProjectResourceService
from core.services.resource import ResourceService
from core.exceptions import ValidationError, BusinessRuleError, NotFoundError
from core.models import Project, ProjectStatus
from ui.styles.style_utils import style_table
from ui.styles.formatting import fmt_currency
from ui.styles.ui_config import UIConfig as CFG, CurrencyType

class ProjectTableModel(QAbstractTableModel):
    # Do not show UUID in the list view; keep useful user-facing columns only
    HEADERS = ["Name", "Client", "Status", "Start", "End", "Budget", "Currency", "Description"]

    def __init__(self, projects: list[Project] | None = None, parent=None):
        super().__init__(parent)
        self._projects: list[Project] = projects or []

    def set_projects(self, projects: list[Project]):
        self.beginResetModel()
        self._projects = projects
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._projects)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        project = self._projects[index.row()]
        col = index.column()

        if col == 0:
            return project.name
        elif col == 1:
            return project.client_name or ""
        elif col == 2:
            return getattr(project.status, "value", str(project.status))
        elif col == 3:
            return project.start_date.isoformat() if project.start_date else ""
        elif col == 4:
            return project.end_date.isoformat() if project.end_date else ""
        elif col == 5:
            return f"{fmt_currency(project.planned_budget)}" if project.planned_budget is not None else ""
        elif col == 6:
            return project.currency or ""
        elif col == 7:
            return (project.description or "")[:80]
        return None

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return super().headerData(section, orientation, role)

    def get_project(self, row: int) -> Optional[Project]:
        if 0 <= row < len(self._projects):
            return self._projects[row]
        return None


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
            ProjectStatus.COMPLETED
        ]
        for s in self._status_values:
            self.status_combo.addItem(s.value)
        
        self.start_date_edit = QDateEdit()
        self.end_date_edit = QDateEdit()
        for date_edit in (self.start_date_edit, self.end_date_edit):
            date_edit.setSizePolicy(CFG.INPUT_POLICY)
            date_edit.setFixedHeight(CFG.INPUT_HEIGHT)
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
                for i,s in enumerate(self._status_values):
                    if s == project.status:
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
            # defaults: today as start date, 
            today = QDate.currentDate()
            self.start_date_edit.setDate(today) 
            self.end_date_edit.setDate(today) 
            self.status_combo.setCurrentIndex(0)  # Planned
            self.currency_combo.setCurrentIndex(1)  # XAF

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
    def planned_budget(self) -> float| None:
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


class ProjectTab(QWidget):
    def __init__(
        self,
        project_service: ProjectService,
        task_service: TaskService,
        reporting_service: ReportingService,
        project_resource_service: ProjectResourceService,
        resource_service: ResourceService,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service = project_service
        self._task_service = task_service
        self._reporting_service = reporting_service
        self._project_resource_service = project_resource_service
        self._resource_service = resource_service

        self._setup_ui()
        self.reload_projects()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )

        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_new = QPushButton(CFG.NEW_PROJECT_LABEL)
        self.btn_edit = QPushButton(CFG.EDIT_LABEL)
        self.btn_delete = QPushButton(CFG.DELETE_LABEL)
        self.btn_refresh = QPushButton(CFG.REFRESH_PROJECTS_LABEL)
        self.btn_project_resources = QPushButton(CFG.PROJECT_RESOURCES_LABEL)
        
        for btn in(
            self.btn_new,
            self.btn_edit,
            self.btn_delete,
            self.btn_refresh,
            self.btn_project_resources,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
        
        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_project_resources)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableView()
        self.model = ProjectTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        style_table(self.table)
        layout.addWidget(self.table)

        # signal connections
        self.btn_new.clicked.connect(self.create_project)
        self.btn_edit.clicked.connect(self.edit_project)
        self.btn_delete.clicked.connect(self.delete_project)
        self.btn_refresh.clicked.connect(self.reload_projects)
        self.btn_project_resources.clicked.connect(self._on_project_resources)

    # ---------------- Actions ---------------- #

    def _on_project_resources(self):
        proj = self._get_selected_project()
        if not proj:
            QMessageBox.information(self, "Project Resources", "Please select a project.")
            return

        dlg = ProjectResourcesDialog(
            project_id=proj.id,
            resource_service=self._resource_service,
            project_resource_service=self._project_resource_service,
            parent=self,
        )
        dlg.exec()
    
    def reload_projects(self):
        projects = self._project_service.list_projects()
        self.model.set_projects(projects)

    def _get_selected_project(self) -> Optional[Project]:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        return self.model.get_project(row)

    def create_project(self):
        dlg = ProjectEditDialog(self)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._project_service.create_project(
                    name=dlg.name,
                    client_name=dlg.client_name,
                    client_contact=dlg.client_contact,
                    planned_budget=dlg.planned_budget,
                    currency=dlg.currency,
                    start_date=dlg.start_date,
                    end_date=dlg.end_date,
                    description=dlg.description,
                )
            except ValidationError as e:
                QMessageBox.warning(self, "Validation error", str(e))
                continue
            self.reload_projects()
            return

    def edit_project(self):
        proj = self._get_selected_project()
        if not proj:
            QMessageBox.information(self, "Edit project", "Please select a project.")
            return

        dlg = ProjectEditDialog(self, project=proj)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._project_service.update_project(
                    project_id=proj.id,
                    name=dlg.name,
                    description=dlg.description,
                    client_name=dlg.client_name,
                    client_contact=dlg.client_contact,
                    planned_budget=dlg.planned_budget,
                    currency=dlg.currency,
                    status=dlg.status,
                    start_date=dlg.start_date,
                    end_date=dlg.end_date,
                )
            except (ValidationError, BusinessRuleError) as e:
                QMessageBox.warning(self, "Error", str(e))
                continue
            self.reload_projects()
            return

    def delete_project(self):
        proj = self._get_selected_project()
        if not proj:
            QMessageBox.information(self, "Delete project", "Please select a project.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm delete",
            f"Delete project '{proj.name}' and all its tasks, costs, etc.?",
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self._project_service.delete_project(proj.id)
        except BusinessRuleError as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        self.reload_projects()
        

class ProjectResourcesDialog(QtWidgets.QDialog):
    """
    Manage Project-Resource membership (planning layer).
    - Add existing master Resources into a specific project
    - Define project-specific hourly rate (override) and planned hours
    """

    def __init__(
        self, project_id: str, 
        resource_service:ResourceService, 
        project_resource_service: ProjectResourceService, 
        parent=None
        ):
        super().__init__(parent)
        self.setWindowTitle("Project Resources")
        self.resize(CFG.DEFAULT_PROJECT_WINDOW_SIZE)

        self._project_id = project_id
        self._resource_service = resource_service
        self._project_resource_service = project_resource_service

        self._table = QtWidgets.QTableWidget(0, 6)
        style_table(self._table)
        self._table.setHorizontalHeaderLabels([
            "Resource",
            "Default Rate",
            "Project Rate",
            "Currency",
            "Planned Hours",
            "Active",
        ])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        hdr.setStretchLastSection(True)
        
        self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
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
        
        # auto-clean orphans so UI stays clean
        valid = []
        for pr in rows:
            try:
                self._resource_service.get_resource(pr.resource_id)
                valid.append(pr)
            except NotFoundError:
                # delete orphan project_resource row
                self._project_resource_service.delete(pr.id)

        rows = valid

        self._table.setRowCount(0)
        for pr in rows:
            # Need resource to show name + defaults
            try:
                res = self._resource_service.get_resource(pr.resource_id)
            except NotFoundError:
                # Resource was deleted or missing; do not crash UI
                res = None

            if not res:
                # Show a placeholder row instead of crashing
                r = self._table.rowCount()
                self._table.insertRow(r)

                item_name = QtWidgets.QTableWidgetItem(f"<missing resource> ({pr.resource_id})")
                item_name.setData(QtCore.Qt.ItemDataRole.UserRole, pr.id)

                # Empty defaults
                self._table.setItem(r, 0, item_name)
                self._table.setItem(r, 1, QtWidgets.QTableWidgetItem(""))
                self._table.setItem(r, 2, QtWidgets.QTableWidgetItem("" if pr.hourly_rate is None else f"{float(pr.hourly_rate):,.2f}"))
                self._table.setItem(r, 3, QtWidgets.QTableWidgetItem((pr.currency_code or "").upper()))
                self._table.setItem(r, 4, QtWidgets.QTableWidgetItem(f"{float(pr.planned_hours or 0.0):,.2f}"))
                self._table.setItem(r, 5, QtWidgets.QTableWidgetItem("Yes" if getattr(pr, "is_active", True) else "No"))
                continue

            r = self._table.rowCount()
            self._table.insertRow(r)

            # store pr.id on first column item
            item_name = QtWidgets.QTableWidgetItem(res.name)
            item_name.setData(QtCore.Qt.ItemDataRole.UserRole, pr.id)

            default_rate = getattr(res, "hourly_rate", None)
            default_cur = getattr(res, "currency_code", "") or ""

            item_def_rate = QtWidgets.QTableWidgetItem("" if default_rate is None else f"{float(default_rate):,.2f}")
            item_proj_rate = QtWidgets.QTableWidgetItem("" if pr.hourly_rate is None else f"{float(pr.hourly_rate):,.2f}")

            # currency: project override else resource default
            cur = (pr.currency_code or default_cur or "").upper()
            item_cur = QtWidgets.QTableWidgetItem(cur)

            item_hours = QtWidgets.QTableWidgetItem(f"{float(pr.planned_hours or 0.0):,.2f}")
            item_active = QtWidgets.QTableWidgetItem("Yes" if getattr(pr, "is_active", True) else "No")

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
    """
    Add/Edit one ProjectResource row.
    """
    def __init__(self, project_id: str, 
                 resource_service: ResourceService, 
                 project_resource_service: ProjectResourceService,
                 project_resource_id: Optional[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Project Resource" if not project_resource_id else "Edit Project Resource")
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

        # allow "blank" rate behavior: use special value text and track user intent
        self._spn_rate.setSpecialValueText("Use resource default")
        self._spn_rate.setValue(0.0)  # means "default" unless user edits
        self._rate_touched = False
        self._spn_rate.valueChanged.connect(lambda _v: setattr(self, "_rate_touched", True))

        # currency touched tracking (empty -> default unless user picks)
        self._currency_touched = False
        self._cmb_currency.currentTextChanged.connect(lambda _t: setattr(self, "_currency_touched", True))
        
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
        # list only ACTIVE master resources
        resources = [r for r in self._resource_service.list_resources() if getattr(r, "is_active", True)]

        self._cmb_resource.clear()
        for r in resources:
            self._cmb_resource.addItem(r.name, r.id)
            
        self._cmb_resource.currentIndexChanged.connect(self._apply_resource_defaults)

        if self._pr_id:
            pr = self._project_resource_service.get(self._pr_id)
            if not pr:
                QtWidgets.QMessageBox.warning(self, "Edit", "Item not found.")
                self.reject()
                return

            # select correct resource
            idx = self._cmb_resource.findData(pr.resource_id)
            if idx >= 0:
                self._cmb_resource.setCurrentIndex(idx)
            self._cmb_resource.setEnabled(False)  # don’t change resource on edit (keeps uniqueness simple)
            # rate
            if pr.hourly_rate is None:
                self._spn_rate.setValue(0.0)  # show "Use resource default"
                self._rate_touched = False
            else:
                self._spn_rate.setValue(float(pr.hourly_rate))
                self._rate_touched = True

            # currency
            cur = (pr.currency_code or "").upper()
            idx = self._cmb_currency.findText(cur)
            if idx >= 0:
                self._cmb_currency.setCurrentIndex(idx)
            else:
                if cur:
                    self._cmb_currency.addItem(cur)
                    self._cmb_currency.setCurrentIndex(self._cmb_currency.count() - 1)
            self._currency_touched = bool(cur)

            # planned hours
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

        # Only apply defaults if user has not touched the fields yet
        if not getattr(self, "_rate_touched", False):
            default_rate = float(getattr(res, "hourly_rate", 0.0) or 0.0)
            # keep as 0.0 => "Use resource default", but show actual value if you want:
            # self._spn_rate.setValue(default_rate)
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

        # Load resource defaults (must exist)
        try:
            res = self._resource_service.get_resource(resource_id)
        except NotFoundError as e:
            QtWidgets.QMessageBox.warning(self, "Save", str(e))
            return

        # rate: if user didn't touch OR value==0 -> use resource default
        rate = None
        if getattr(self, "_rate_touched", False) and self._spn_rate.value() > 0:
            rate = float(self._spn_rate.value())
        else:
            default_rate = getattr(res, "hourly_rate", None)
            rate = float(default_rate) if default_rate is not None else None

        # currency: if user didn't touch OR empty -> use resource default
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
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Save failed", str(e))
            return

        self.accept()


