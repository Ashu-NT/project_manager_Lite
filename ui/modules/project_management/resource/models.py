from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from core.modules.project_management.domain.resource import Resource
from ui.platform.shared.table_model import horizontal_header_data


class ResourceTableModel(QAbstractTableModel):
    HEADERS = [
        "Name",
        "Role",
        "Worker",
        "Category",
        "Hourly rate",
        "Capacity",
        "Currency",
        "Context",
        "Contact",
        "Active",
    ]

    def __init__(
        self,
        resources: list[Resource] | None = None,
        *,
        employee_context_by_id: dict[str, str] | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._resources: list[Resource] = resources or []
        self._employee_context_by_id: dict[str, str] = employee_context_by_id or {}

    def set_resources(self, resources: list[Resource]):
        self.beginResetModel()
        self._resources = resources
        self.endResetModel()

    def set_employee_contexts(self, employee_context_by_id: dict[str, str] | None) -> None:
        self.beginResetModel()
        self._employee_context_by_id = employee_context_by_id or {}
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
            return getattr(getattr(r, "worker_type", None), "value", "").title() or "External"
        if col == 3:
            return getattr(r, "cost_type", None).value if getattr(r, "cost_type", None) else ""
        if col == 4:
            return f"{(r.hourly_rate or 0.0):.2f}"
        if col == 5:
            return f"{float(getattr(r, 'capacity_percent', 100.0) or 100.0):.1f}%"
        if col == 6:
            return r.currency_code or ""
        if col == 7:
            employee_id = str(getattr(r, "employee_id", "") or "").strip()
            return self._employee_context_by_id.get(employee_id, "")
        if col == 8:
            return getattr(r, "contact", "") or ""
        if col == 9:
            return "Yes" if getattr(r, "is_active", True) else "No"
        return None

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        return horizontal_header_data(
            self.HEADERS,
            section,
            orientation,
            role,
            super().headerData,
        )

    def get_resource(self, row: int) -> Optional[Resource]:
        if 0 <= row < len(self._resources):
            return self._resources[row]
        return None


__all__ = ["ResourceTableModel"]
