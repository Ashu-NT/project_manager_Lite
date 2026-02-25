from __future__ import annotations

from PySide6.QtWidgets import QDialog, QMessageBox

from core.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from core.services.project import ProjectResourceService
from core.services.resource import ResourceService
from core.services.task import TaskService
from ui.task.dialogs import (
    DependencyListDialog,
    TaskEditDialog,
    TaskProgressDialog,
)


class TaskActionsMixin:
    _task_service: TaskService
    _resource_service: ResourceService
    _project_resource_service: ProjectResourceService

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
            except (ValidationError, BusinessRuleError, NotFoundError, ConcurrencyError) as exc:
                QMessageBox.warning(self, "Error", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Error", str(exc))
                return
            self.reload_tasks()
            return

    def edit_task(self):
        task = self._get_selected_task()
        if not task:
            QMessageBox.information(self, "Edit task", "Please select a task.")
            return

        dlg = TaskEditDialog(self, task=task)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._task_service.update_task(
                    task_id=task.id,
                    name=dlg.name,
                    description=dlg.description,
                    start_date=dlg.start_date,
                    duration_days=dlg.duration_days,
                    status=dlg.status,
                    priority=dlg.priority,
                    deadline=dlg.deadline,
                )
            except (ValidationError, BusinessRuleError, NotFoundError, ConcurrencyError) as exc:
                QMessageBox.warning(self, "Error", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Error", str(exc))
                return
            self.reload_tasks()
            return

    def delete_task(self):
        task = self._get_selected_task()
        if not task:
            QMessageBox.information(self, "Delete task", "Please select a task.")
            return
        confirm = QMessageBox.question(
            self,
            "Delete task",
            f"Delete task '{task.name}' (and its dependencies, assignments, etc.)?",
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            self._task_service.delete_task(task.id)
        except (BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))
            return
        self.reload_tasks()

    def update_progress(self):
        task = self._get_selected_task()
        if not task:
            QMessageBox.information(self, "Update progress", "Please select a task.")
            return

        dlg = TaskProgressDialog(self, task=task)
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

                if not kwargs:
                    QMessageBox.information(
                        self,
                        "Update progress",
                        "Please select at least one field to update.",
                    )
                    continue

                self._task_service.update_progress(task_id=task.id, **kwargs)
            except (ValidationError, BusinessRuleError, NotFoundError, ConcurrencyError) as exc:
                QMessageBox.warning(self, "Error", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Error", str(exc))
                return
            self.reload_tasks()
            return

    def manage_dependencies(self):
        project_id = self._current_project_id()
        if not project_id:
            QMessageBox.information(self, "Dependencies", "Please select a project.")
            return
        task = self._get_selected_task()
        if not task:
            QMessageBox.information(self, "Dependencies", "Please select a task.")
            return
        try:
            project_tasks = self._task_service.list_tasks_for_project(project_id)
        except (BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Dependencies", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Dependencies", str(exc))
            return
        dlg = DependencyListDialog(self, self._task_service, project_tasks, task)
        dlg.exec()
        self.reload_tasks()

    def manage_assignments(self):
        task = self._get_selected_task()
        if not task:
            QMessageBox.information(self, "Assignments", "Please select a task.")
            return

        refresh_panel = getattr(self, "_reload_assignment_panel_for_selected_task", None)
        if callable(refresh_panel):
            refresh_panel()

        assignment_table = getattr(self, "assignment_table", None)
        if assignment_table is not None:
            try:
                assignment_table.setFocus()
            except Exception:
                pass
