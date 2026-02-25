from __future__ import annotations

from PySide6.QtWidgets import QComboBox

from core.services.project import ProjectService
from ui.shared.combo import current_data_and_text


class ReportProjectFlowMixin:
    project_combo: QComboBox
    _project_service: ProjectService

    def _load_projects(self) -> None:
        previous_id = self._current_project_id_and_name()[0]
        self.project_combo.clear()
        projects = self._project_service.list_projects()
        for project in projects:
            self.project_combo.addItem(project.name, userData=project.id)
        if previous_id:
            idx = self.project_combo.findData(previous_id)
            if idx >= 0:
                self.project_combo.setCurrentIndex(idx)

    def _on_project_changed_event(self, _project_id: str) -> None:
        self._load_projects()

    def _current_project_id_and_name(self) -> tuple[str | None, str | None]:
        return current_data_and_text(self.project_combo)


__all__ = ["ReportProjectFlowMixin"]
