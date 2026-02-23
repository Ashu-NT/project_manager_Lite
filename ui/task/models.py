from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from core.models import Task


class TaskTableModel(QAbstractTableModel):
    HEADERS = [
        "Name",
        "Status",
        "Start",
        "End",
        "Duration",
        "%",
        "Deadline",
        "Priority",
        "Actual Start",
        "Actual End",
    ]

    def __init__(self, tasks: list[Task] | None = None, parent=None):
        super().__init__(parent)
        self._tasks: list[Task] = tasks or []

    def set_tasks(self, tasks: list[Task]):
        self.beginResetModel()
        self._tasks = tasks or []
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._tasks)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.TextAlignmentRole and index.column() in (4, 5, 7):
            return Qt.AlignRight | Qt.AlignVCenter
        if role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        t = self._tasks[index.row()]
        col = index.column()

        if col == 0:
            return t.name
        if col == 1:
            return getattr(t.status, "value", str(t.status))
        if col == 2:
            return t.start_date.isoformat() if t.start_date else ""
        if col == 3:
            return t.end_date.isoformat() if t.end_date else ""
        if col == 4:
            return t.duration_days if t.duration_days is not None else ""
        if col == 5:
            return f"{(t.percent_complete or 0.0):.0f}"
        if col == 6:
            return t.deadline.isoformat() if getattr(t, "deadline", None) else ""
        if col == 7:
            return t.priority if t.priority is not None else ""
        if col == 8:
            return t.actual_start.isoformat() if getattr(t, "actual_start", None) else ""
        if col == 9:
            return t.actual_end.isoformat() if getattr(t, "actual_end", None) else ""
        return None

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return super().headerData(section, orientation, role)

    def get_task(self, row: int) -> Optional[Task]:
        if 0 <= row < len(self._tasks):
            return self._tasks[row]
        return None
