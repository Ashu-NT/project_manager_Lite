from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.exceptions import BusinessRuleError, ValidationError
from core.models import Project
from core.services.project import ProjectResourceService, ProjectService
from core.services.reporting import ReportingService
from core.services.resource import ResourceService
from core.services.task import TaskService
from ui.project.dialogs import ProjectEditDialog
from ui.project.models import ProjectTableModel
from ui.project.resource_panel import ProjectResourcePanelMixin
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class ProjectTab(ProjectResourcePanelMixin, QWidget):
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
        self._project_service: ProjectService = project_service
        self._task_service: TaskService = task_service
        self._reporting_service: ReportingService = reporting_service
        self._project_resource_service: ProjectResourceService = project_resource_service
        self._resource_service: ResourceService = resource_service

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

        for btn in(
            self.btn_new,
            self.btn_edit,
            self.btn_delete,
            self.btn_refresh,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)

        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh)

        layout.addLayout(toolbar)

        content = QSplitter(Qt.Horizontal)
        content.setChildrenCollapsible(False)
        content.setHandleWidth(8)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.table = QTableView()
        self.model = ProjectTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        style_table(self.table)
        left_layout.addWidget(self.table)

        right_panel = self._build_project_resource_panel()
        right_panel.setMinimumWidth(360)

        content.addWidget(left_panel)
        content.addWidget(right_panel)
        content.setStretchFactor(0, 5)
        content.setStretchFactor(1, 3)
        content.setSizes([900, 520])
        layout.addWidget(content, 1)

        # signal connections
        self.btn_new.clicked.connect(self.create_project)
        self.btn_edit.clicked.connect(self.edit_project)
        self.btn_delete.clicked.connect(self.delete_project)
        self.btn_refresh.clicked.connect(self.reload_projects)
        self.table.selectionModel().selectionChanged.connect(self._on_project_selection_changed)

    def reload_projects(self):
        selected = self._get_selected_project()
        selected_id = selected.id if selected else None
        projects = self._project_service.list_projects()
        self.model.set_projects(projects)
        if not projects:
            self._reload_project_resource_panel_for_selected_project()
            return
        row = 0
        if selected_id:
            for i, p in enumerate(projects):
                if p.id == selected_id:
                    row = i
                    break
        self.table.selectRow(row)
        self._reload_project_resource_panel_for_selected_project()

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

