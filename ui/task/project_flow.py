from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QComboBox, QTableView

from core.models import Task
from core.services.project import ProjectService
from core.services.task import TaskService
from ui.task.models import TaskTableModel
from ui.shared.combo import current_data


class TaskProjectFlowMixin:
    project_combo: QComboBox
    table: QTableView
    model: TaskTableModel
    _project_service: ProjectService
    _task_service: TaskService

    def _on_task_changed(self, project_id: str):
        current_pid = self._current_project_id()
        if current_pid == project_id:
            self.reload_tasks()

    def _on_project_changed_event(self, _project_id: str):
        prev_pid = self._current_project_id()
        projects = self._project_service.list_projects()
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for project in projects:
            self.project_combo.addItem(project.name, userData=project.id)
        self.project_combo.blockSignals(False)

        if prev_pid and prev_pid in [p.id for p in projects]:
            index = self.project_combo.findData(prev_pid)
            if index != -1:
                self.project_combo.setCurrentIndex(index)
        elif self.project_combo.count() > 0:
            self.project_combo.setCurrentIndex(0)

        self.reload_tasks()

    def _on_resources_changed(self, _resource_id: str) -> None:
        post_reload = getattr(self, "_reload_assignment_panel_for_selected_task", None)
        if callable(post_reload):
            post_reload()

    def _load_projects(self):
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        projects = self._project_service.list_projects()
        for project in projects:
            self.project_combo.addItem(project.name, userData=project.id)
        self.project_combo.blockSignals(False)
        if self.project_combo.count() > 0:
            self.project_combo.setCurrentIndex(0)
            self._on_project_changed(0)

    def _current_project_id(self) -> Optional[str]:
        return current_data(self.project_combo)

    def _on_project_changed(self, _index: int):
        self.reload_tasks()

    def reload_tasks(self):
        current_task = self._get_selected_task()
        current_task_id = current_task.id if current_task else None
        project_id = self._current_project_id()
        if not project_id:
            self.model.set_tasks([])
            post_reload = getattr(self, "_reload_assignment_panel_for_selected_task", None)
            if callable(post_reload):
                post_reload()
            return

        tasks = self._task_service.list_tasks_for_project(project_id)
        self.model.set_tasks(tasks)

        if current_task_id:
            self._select_task_by_id(current_task_id)
        elif tasks:
            self.table.selectRow(0)

        post_reload = getattr(self, "_reload_assignment_panel_for_selected_task", None)
        if callable(post_reload):
            post_reload()

    def _get_selected_task(self) -> Optional[Task]:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        return self.model.get_task(row)

    def _select_task_by_id(self, task_id: str) -> None:
        for row in range(self.model.rowCount()):
            task = self.model.get_task(row)
            if task and task.id == task_id:
                self.table.selectRow(row)
                return
