from __future__ import annotations

from typing import Any, Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from core.models import CostItem, CostType, Task
from ui.shared.table_model import horizontal_header_data
from ui.styles.formatting import fmt_currency, currency_symbol_from_code
from ui.styles.ui_config import UIConfig as CFG


class CostTableModel(QAbstractTableModel):
    HEADERS = ["Description", "Task", "Type", "Planned", "Committed", "Actual", "Incurred Date"]

    def __init__(self, costs: list[CostItem] | None = None, parent=None):
        super().__init__(parent)
        self._costs: list[CostItem] = costs or []
        self._task_names: dict[str, str] = {}
        self._project_currency: str = ""
        self._tasks_by_id: dict[str, Task] = {}

    def set_context(self, tasks_by_id: dict[str, Task], project_currency: str = ""):
        self._tasks_by_id = tasks_by_id or {}
        self._project_currency = (project_currency or "").strip().upper()
        self.layoutChanged.emit()

    def set_costs(self, costs: list[CostItem], task_names: dict[str, str]):
        self.beginResetModel()
        self._costs = costs
        self._task_names = task_names
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._costs)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        col = index.column()
        if role == Qt.TextAlignmentRole and col in (3, 4, 5):
            return Qt.AlignRight | Qt.AlignVCenter
        if role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        c = self._costs[index.row()]
        if col == 0:
            return c.description
        if col == 1:
            if c.task_id and c.task_id in self._task_names:
                return self._task_names[c.task_id]
            return ""
        if col == 2:
            if getattr(c, "cost_type", None) == CostType.LABOR:
                return CFG.COST_TYPE_LABOR_ADJUSTMENT_LABEL
            return c.cost_type.value if hasattr(c.cost_type, "value") else str(c.cost_type)
        if col == 3:
            return fmt_currency(c.planned_amount, currency_symbol_from_code(c.currency_code or self._project_currency))
        if col == 4:
            return fmt_currency(c.committed_amount, currency_symbol_from_code(c.currency_code or self._project_currency))
        if col == 5:
            return fmt_currency(c.actual_amount, currency_symbol_from_code(c.currency_code or self._project_currency))
        if col == 6:
            return c.incurred_date.isoformat() if c.incurred_date else ""
        return None

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        return horizontal_header_data(
            self.HEADERS,
            section,
            orientation,
            role,
            super().headerData,
        )

    def get_cost(self, row: int) -> Optional[CostItem]:
        if 0 <= row < len(self._costs):
            return self._costs[row]
        return None


class LaborPlanVsActualTableModel(QAbstractTableModel):
    HEADERS = [
        "Resource",
        "Planned Hours",
        "Planned Cost",
        "Actual Hours",
        "Actual Cost",
        "Variance",
        "Currency",
    ]

    def __init__(self, rows):
        super().__init__()
        self._rows: list[Any] = rows or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        row = self._rows[index.row()]
        col = index.column()

        cur = (row.actual_currency_code or row.planned_currency_code or "").upper()
        sym = currency_symbol_from_code(cur)

        if col == 0:
            return row.resource_name
        if col == 1:
            return f"{float(row.planned_hours or 0.0):.2f}"
        if col == 2:
            return fmt_currency(float(row.planned_cost or 0.0), sym)
        if col == 3:
            return f"{float(row.actual_hours or 0.0):.2f}"
        if col == 4:
            return fmt_currency(float(row.actual_cost or 0.0), sym)
        if col == 5:
            return fmt_currency(float(row.variance_cost or 0.0), sym)
        if col == 6:
            return cur or ""
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        return horizontal_header_data(
            self.HEADERS,
            section,
            orientation,
            role,
            super().headerData,
        )

    def get_row(self, row: int):
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None


__all__ = ["CostTableModel", "LaborPlanVsActualTableModel"]
