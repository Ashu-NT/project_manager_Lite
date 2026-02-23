from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from core.models import TaskAssignment


@dataclass(frozen=True)
class AssignmentRow:
    assignment: TaskAssignment
    resource_name: str


class AssignmentTableModel(QAbstractTableModel):
    HEADERS = ["Resource", "Allocation (%)", "Hours Logged"]

    def __init__(self, rows: list[AssignmentRow] | None = None, parent=None):
        super().__init__(parent)
        self._rows: list[AssignmentRow] = rows or []

    def set_rows(self, rows: list[AssignmentRow]) -> None:
        self.beginResetModel()
        self._rows = rows or []
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        col = index.column()
        assignment = row.assignment

        if role == Qt.TextAlignmentRole and col in (1, 2):
            return Qt.AlignRight | Qt.AlignVCenter

        if role not in (Qt.DisplayRole, Qt.EditRole):
            return None

        if col == 0:
            return row.resource_name
        if col == 1:
            return f"{float(assignment.allocation_percent or 0.0):.1f}"
        if col == 2:
            return f"{float(assignment.hours_logged or 0.0):.2f}"
        return None

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return super().headerData(section, orientation, role)

    def get_assignment(self, row: int) -> Optional[TaskAssignment]:
        if 0 <= row < len(self._rows):
            return self._rows[row].assignment
        return None


__all__ = ["AssignmentRow", "AssignmentTableModel"]
