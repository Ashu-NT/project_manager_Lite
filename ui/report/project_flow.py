from __future__ import annotations

from PySide6.QtWidgets import QComboBox

from core.services.project import ProjectService


class ReportProjectFlowMixin:
    project_combo: QComboBox
    _project_service: ProjectService

    def _load_projects(self) -> None:
        self.project_combo.clear()
        for project in self._project_service.list_projects():
            self.project_combo.addItem(project.name, userData=project.id)

    def _current_project_id_and_name(self) -> tuple[str | None, str | None]:
        idx = self.project_combo.currentIndex()
        if idx < 0:
            return None, None
        return self.project_combo.itemData(idx), self.project_combo.currentText()


__all__ = ["ReportProjectFlowMixin"]
