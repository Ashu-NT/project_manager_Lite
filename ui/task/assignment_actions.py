from __future__ import annotations

from PySide6.QtWidgets import QDialog, QInputDialog, QMessageBox

from core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.services.project import ProjectResourceService
from core.services.resource import ResourceService
from core.services.task import TaskService
from ui.task.dialogs import AssignmentAddDialog


class TaskAssignmentActionsMixin:
    _task_service: TaskService
    _resource_service: ResourceService
    _project_resource_service: ProjectResourceService

    def _show_overallocation_warning_if_any(self) -> None:
        consume = getattr(self._task_service, "consume_last_overallocation_warning", None)
        if not callable(consume):
            return
        warning = consume()
        if warning:
            QMessageBox.information(self, "Allocation Warning", warning)

    def add_assignment_inline(self) -> None:
        task = self._get_selected_task()
        if not task:
            QMessageBox.information(self, "Assignments", "Please select a task.")
            return

        project_resources = self._project_resource_service.list_by_project(task.project_id)
        if not project_resources:
            QMessageBox.information(
                self,
                "Assignments",
                "No project resources found.\n\nAdd resources in Project -> Project Resources first.",
            )
            return

        resources = self._resource_service.list_resources()
        resources_by_id = {resource.id: resource for resource in resources}
        dlg = AssignmentAddDialog(
            self,
            project_resources=project_resources,
            resources_by_id=resources_by_id,
        )
        if dlg.exec() != QDialog.Accepted:
            return

        project_resource_id = dlg.project_resource_id
        if not project_resource_id:
            QMessageBox.warning(self, "Assignments", "Please select a project resource.")
            return

        try:
            self._task_service.assign_project_resource(
                task_id=task.id,
                project_resource_id=project_resource_id,
                allocation_percent=dlg.allocation_percent,
            )
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return

        self._show_overallocation_warning_if_any()
        self.reload_tasks()
        self._select_task_by_id(task.id)

    def remove_assignment_inline(self) -> None:
        assignment = self._get_selected_assignment()
        if not assignment:
            QMessageBox.information(self, "Assignments", "Please select an assignment.")
            return

        confirm = QMessageBox.question(
            self,
            "Remove assignment",
            "Remove selected assignment?",
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self._task_service.unassign_resource(assignment.id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return

        self.reload_tasks()
        self._select_task_by_id(assignment.task_id)

    def set_assignment_allocation_inline(self) -> None:
        assignment = self._get_selected_assignment()
        if not assignment:
            QMessageBox.information(self, "Assignments", "Please select an assignment.")
            return

        value, ok = QInputDialog.getDouble(
            self,
            "Set allocation",
            "Allocation (%):",
            float(getattr(assignment, "allocation_percent", 0.0) or 0.0),
            0.1,
            100.0,
            1,
        )
        if not ok:
            return

        try:
            self._task_service.set_assignment_allocation(
                assignment_id=assignment.id,
                allocation_percent=value,
            )
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return

        self._show_overallocation_warning_if_any()
        self.reload_tasks()
        self._select_task_by_id(assignment.task_id)

    def log_assignment_hours_inline(self) -> None:
        assignment = self._get_selected_assignment()
        if not assignment:
            QMessageBox.information(self, "Assignments", "Please select an assignment.")
            return

        value, ok = QInputDialog.getDouble(
            self,
            "Log hours",
            "Hours logged:",
            float(getattr(assignment, "hours_logged", 0.0) or 0.0),
            0.0,
            1000000.0,
            2,
        )
        if not ok:
            return

        try:
            self._task_service.set_assignment_hours(assignment.id, value)
        except (ValidationError, BusinessRuleError, NotFoundError) as exc:
            QMessageBox.warning(self, "Error", str(exc))
            return

        self.reload_tasks()
        self._select_task_by_id(assignment.task_id)
