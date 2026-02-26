from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QMessageBox

from core.exceptions import BusinessRuleError
from core.services.auth.authorization import require_permission
from core.services.project import ProjectService
from core.services.scheduling import SchedulingEngine
from core.services.task import TaskService
from ui.shared.async_job import JobUiConfig, start_async_job
from ui.shared.worker_services import worker_service_scope


class CalendarProjectOpsMixin:
    _project_service: ProjectService
    _task_service: TaskService
    _scheduling_engine: SchedulingEngine
    project_combo: QComboBox

    def _on_project_changed(self, project_id: str):
        prev_pid = self.project_combo.currentData()
        projects = self._project_service.list_projects()
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for p in projects:
            self.project_combo.addItem(p.name, userData=p.id)
        self.project_combo.blockSignals(False)
        if not projects:
            return

        target = None
        if prev_pid and any(p.id == prev_pid for p in projects):
            target = prev_pid
        elif project_id and any(p.id == project_id for p in projects):
            target = project_id
        else:
            target = projects[0].id

        idx = self.project_combo.findData(target)
        if idx >= 0:
            self.project_combo.setCurrentIndex(idx)

    def reload_projects(self):
        self.project_combo.clear()
        projects = self._project_service.list_projects()
        for p in projects:
            self.project_combo.addItem(p.name, userData=p.id)

    def recalc_project_schedule(self):
        idx = self.project_combo.currentIndex()
        if idx < 0:
            QMessageBox.information(self, "Schedule", "Please select a project.")
            return
        pid = self.project_combo.itemData(idx)
        name = self.project_combo.currentText()
        try:
            require_permission(
                getattr(self._task_service, "_user_session", None),
                "task.manage",
                operation_label="recalculate schedule",
            )
        except BusinessRuleError as e:
            QMessageBox.warning(self, "Error", str(e))
            return

        def _work(token, progress):
            token.raise_if_cancelled()
            progress(None, "Schedule recalculation started...")
            with worker_service_scope(getattr(self._task_service, "_user_session", None)) as services:
                token.raise_if_cancelled()
                schedule = services["scheduling_engine"].recalculate_project_schedule(pid)
                token.raise_if_cancelled()
                return len(schedule)

        start_async_job(
            parent=self,
            ui=JobUiConfig(
                title="Recalculate Schedule",
                label="Recalculating project schedule...",
                allow_retry=True,
            ),
            work=_work,
            on_success=lambda task_count: QMessageBox.information(
                self,
                "Schedule recalculated",
                f"Schedule recalculated for project '{name}'.\n"
                f"Tasks updated: {task_count}.\n\n"
                "Tip: Open the Tasks or Reports tab to see the updated dates and Gantt.",
            ),
            on_error=lambda msg: QMessageBox.critical(self, "Error", msg),
            on_cancel=lambda: QMessageBox.information(
                self,
                "Schedule",
                "Schedule recalculation canceled.",
            ),
        )
