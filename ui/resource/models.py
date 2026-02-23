from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from core.models import Resource


class ResourceTableModel(QAbstractTableModel):
    HEADERS = ["Name", "Role", "Category", "Hourly rate", "Currency", "Active"]

    def __init__(self, resources: list[Resource] | None = None, parent=None):
        super().__init__(parent)
        self._resources: list[Resource] = resources or []

    def set_resources(self, resources: list[Resource]):
        self.beginResetModel()
        self._resources = resources
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._resources)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        r = self._resources[index.row()]
        col = index.column()
        if col == 0:
            return r.name
        if col == 1:
            return r.role or ""
        if col == 2:
            return getattr(r, "cost_type", None).value if getattr(r, "cost_type", None) else ""
        if col == 3:
            return f"{(r.hourly_rate or 0.0):.2f}"
        if col == 4:
            return r.currency_code or ""
        if col == 5:
            return "Yes" if getattr(r, "is_active", True) else "No"
        return None

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return super().headerData(section, orientation, role)

    def get_resource(self, row: int) -> Optional[Resource]:
        if 0 <= row < len(self._resources):
            return self._resources[row]
        return None


__all__ = ["ResourceTableModel"]
