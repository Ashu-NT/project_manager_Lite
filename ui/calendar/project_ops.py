from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QMessageBox

from core.exceptions import BusinessRuleError
from core.services.project import ProjectService
from core.services.scheduling import SchedulingEngine


class CalendarProjectOpsMixin:
    _project_service: ProjectService
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
            schedule = self._scheduling_engine.recalculate_project_schedule(pid)
        except BusinessRuleError as e:
            QMessageBox.warning(self, "Error", str(e))
            return

        QMessageBox.information(
            self,
            "Schedule recalculated",
            f"Schedule recalculated for project '{name}'.\n"
            f"Tasks updated: {len(schedule)}.\n\n"
            "Tip: Open the Tasks or Reports tab to see the updated dates and Gantt.",
        )
