# ui/task/tab.py
from __future__ import annotations
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTableView, QDialog, QMessageBox
)

from core.services.project import ProjectService
from core.services.project import ProjectResourceService
from core.services.task import TaskService
from core.services.resource import ResourceService
from core.exceptions import ValidationError, BusinessRuleError, NotFoundError
from core.models import Task
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG
from core.events.domain_events import domain_events
from .components import (
    TaskTableModel,
    TaskEditDialog,
    TaskProgressDialog,
    DependencyListDialog,
    AssignmentListDialog,
)

class TaskTab(QWidget):
    def __init__(
        self,
        project_service: ProjectService,
        task_service: TaskService,
        resource_service: ResourceService,
        project_resource_service: ProjectResourceService,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service = project_service
        self._task_service = task_service
        self._resource_service = resource_service
        self._project_resource_service = project_resource_service

        self._setup_ui()
        self._load_projects()
        domain_events.tasks_changed.connect(self._on_task_changed)
        domain_events.project_changed.connect(self._on_project_changed_event)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        self.setMinimumSize(self.sizeHint())
        
        # Top: project selector
        top = QHBoxLayout()
        top.addWidget(QLabel("Project:"))
        self.project_combo = QComboBox()
        self.project_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        
        self.btn_reload_projects = QPushButton(CFG.RELOAD_PROJECTS_LABEL)
        top.addWidget(self.project_combo)
        top.addWidget(self.btn_reload_projects)
        top.addStretch()
        layout.addLayout(top)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_new = QPushButton(CFG.NEW_TASK_LABEL)
        self.btn_edit = QPushButton(CFG.EDIT_LABEL)
        self.btn_delete = QPushButton(CFG.DELETE_LABEL)
        self.btn_progress = QPushButton(CFG.UPDATE_PROGRESS_LABEL)
        self.btn_deps = QPushButton(CFG.DEPENDENCIES_LABEL)
        self.btn_assign = QPushButton(CFG.ASSIGNMENTS_LABEL)
        self.btn_refresh_tasks = QPushButton(CFG.REFRESH_TASKS_LABEL)
        
        for btn in [
            self.btn_reload_projects,
            self.btn_new,
            self.btn_edit,
            self.btn_delete,
            self.btn_progress,
            self.btn_deps,
            self.btn_assign,
            self.btn_refresh_tasks,
        ]:
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
        
        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_progress)
        toolbar.addWidget(self.btn_deps)
        toolbar.addWidget(self.btn_assign)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh_tasks)
        layout.addLayout(toolbar)

        # Table of tasks
        self.table = QTableView()
        self.model = TaskTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        style_table(self.table)
        layout.addWidget(self.table)

        # Signals
        self.btn_reload_projects.clicked.connect(self._load_projects)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.btn_refresh_tasks.clicked.connect(self.reload_tasks)
        self.btn_new.clicked.connect(self.create_task)
        self.btn_edit.clicked.connect(self.edit_task)
        self.btn_delete.clicked.connect(self.delete_task)
        self.btn_progress.clicked.connect(self.update_progress)
        self.btn_deps.clicked.connect(self.manage_dependencies)
        self.btn_assign.clicked.connect(self.manage_assignments)

    # ------------- Helpers ------------- #
    def _on_task_changed(self, project_id: str):
        current_pid = self._current_project_id()
        if current_pid == project_id:
            self.reload_tasks()
    
    def _on_project_changed_event(self, project_id: str):
        # Preserve current selection (if still valid) while reloading projects
        prev_pid = self._current_project_id()
        projects = self._project_service.list_projects()
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        # Re-populate combo box with updated project list
        for p in projects:
            self.project_combo.addItem(p.name, userData=p.id)
        self.project_combo.blockSignals(False)
        # If the previously selected project still exists, keep it selected
        if prev_pid and prev_pid in [p.id for p in projects]:
            index = self.project_combo.findData(prev_pid)
            if index != -1:
                self.project_combo.setCurrentIndex(index)
        else:
            # If no previous project or it was deleted, default to first
            if self.project_combo.count() > 0:
                self.project_combo.setCurrentIndex(0)
        # Finally, refresh the task list for the (new) current project
        self.reload_tasks()
    
    def _load_projects(self):
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        projects = self._project_service.list_projects()
        for p in projects:
            self.project_combo.addItem(p.name, userData=p.id)
        self.project_combo.blockSignals(False)
        if self.project_combo.count() > 0:
            self.project_combo.setCurrentIndex(0)
            self._on_project_changed(0)

    def _current_project_id(self) -> Optional[str]:
        idx = self.project_combo.currentIndex()
        if idx < 0:
            return None
        return self.project_combo.itemData(idx)

    def _on_project_changed(self, index: int):
        self.reload_tasks()

    def reload_tasks(self):
        pid = self._current_project_id()
        if not pid:
            self.model.set_tasks([])
            return
        tasks = self._task_service.list_tasks_for_project(pid)
        self.model.set_tasks(tasks)

    def _get_selected_task(self) -> Optional[Task]:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        return self.model.get_task(row)

    # ------------- Actions ------------- #

    def create_task(self):
        pid = self._current_project_id()
        if not pid:
            QMessageBox.information(self, "New task", "Please select a project.")
            return

        dlg = TaskEditDialog(self, task=None)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._task_service.create_task(
                    project_id=pid,
                    name=dlg.name,
                    description=dlg.description,
                    start_date=dlg.start_date,
                    duration_days=dlg.duration_days,
                    status=dlg.status,
                    priority=dlg.priority,
                    deadline=dlg.deadline,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as e:
                    QMessageBox.warning(self, "Error", str(e))
                    continue
            self.reload_tasks()
            return

    def edit_task(self):
        t = self._get_selected_task()
        if not t:
            QMessageBox.information(self, "Edit task", "Please select a task.")
            return

        dlg = TaskEditDialog(self, task=t)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._task_service.update_task(
                    task_id=t.id,
                    name=dlg.name,
                    description=dlg.description,
                    start_date=dlg.start_date,
                    duration_days=dlg.duration_days,
                    status=dlg.status,
                    priority=dlg.priority,
                    deadline=dlg.deadline,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as e:
                    QMessageBox.warning(self, "Error", str(e))
                    continue
            self.reload_tasks()
            return

    def delete_task(self):
        t = self._get_selected_task()
        if not t:
            QMessageBox.information(self, "Delete task", "Please select a task.")
            return
        confirm = QMessageBox.question(
            self,
            "Delete task",
            f"Delete task '{t.name}' (and its dependencies, assignments, etc.)?",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self._task_service.delete_task(t.id)
        except BusinessRuleError as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        self.reload_tasks()

    def update_progress(self):
        t = self._get_selected_task()
        if not t:
            QMessageBox.information(self, "Update progress", "Please select a task.")
            return

        dlg = TaskProgressDialog(self, task=t)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                kwargs = {}
                if dlg.percent_set:
                    kwargs["percent_complete"] = dlg.percent_complete
                if dlg.actual_start_set:
                    kwargs["actual_start"] = dlg.actual_start
                if dlg.actual_end_set:
                    kwargs["actual_end"] = dlg.actual_end

                # if nothing selected, warn user
                if not kwargs:
                    QMessageBox.information(self, "Update progress", "Please select at least one field to update.")
                    continue

                self._task_service.update_progress(task_id=t.id, **kwargs)
            except (ValidationError, BusinessRuleError, NotFoundError) as e:
                QMessageBox.warning(self, "Error", str(e))
                continue
            self.reload_tasks()
            return

    def manage_dependencies(self):
        pid = self._current_project_id()
        if not pid:
            QMessageBox.information(self, "Dependencies", "Please select a project.")
            return
        t = self._get_selected_task()
        if not t:
            QMessageBox.information(self, "Dependencies", "Please select a task.")
            return
        project_tasks = self._task_service.list_tasks_for_project(pid)
        dlg = DependencyListDialog(self, self._task_service, project_tasks, t)
        dlg.exec()
        self.reload_tasks()

    def manage_assignments(self):
        t = self._get_selected_task()
        if not t:
            QMessageBox.information(self, "Assignments", "Please select a task.")
            return
        dlg = AssignmentListDialog(self, self._task_service, self._resource_service, self._project_resource_service, t)
        dlg.exec()
        self.reload_tasks()

