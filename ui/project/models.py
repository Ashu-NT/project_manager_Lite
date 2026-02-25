from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex

from core.models import Project
from ui.shared.table_model import horizontal_header_data
from ui.styles.formatting import fmt_currency


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
        return horizontal_header_data(
            self.HEADERS,
            section,
            orientation,
            role,
            super().headerData,
        )

    def get_project(self, row: int) -> Optional[Project]:
        if 0 <= row < len(self._projects):
            return self._projects[row]
        return None

