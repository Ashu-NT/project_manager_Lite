from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLineEdit

from core.models import CostType


class CostFiltersMixin:
    filter_text: QLineEdit
    filter_type_combo: QComboBox
    filter_task_combo: QComboBox
    _project_tasks: list

    def _reload_cost_type_filter_options(self) -> None:
        selected = self.filter_type_combo.currentData() if self.filter_type_combo.count() else ""
        self.filter_type_combo.blockSignals(True)
        self.filter_type_combo.clear()
        self.filter_type_combo.addItem("All Types", userData="")
        for cost_type in CostType:
            self.filter_type_combo.addItem(cost_type.value, userData=cost_type.value)
        idx = self.filter_type_combo.findData(selected)
        self.filter_type_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.filter_type_combo.blockSignals(False)

    def _reload_task_filter_options(self) -> None:
        selected = self.filter_task_combo.currentData() if self.filter_task_combo.count() else ""
        self.filter_task_combo.blockSignals(True)
        self.filter_task_combo.clear()
        self.filter_task_combo.addItem("All Tasks", userData="")
        for task in sorted(self._project_tasks, key=lambda t: t.name.lower()):
            self.filter_task_combo.addItem(task.name, userData=task.id)
        idx = self.filter_task_combo.findData(selected)
        self.filter_task_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.filter_task_combo.blockSignals(False)

    def _clear_cost_filters(self) -> None:
        self.filter_text.clear()
        self.filter_type_combo.setCurrentIndex(0)
        self.filter_task_combo.setCurrentIndex(0)
        self.reload_costs()

    def _apply_cost_filters(self, costs, task_names: dict[str, str]):
        text = self.filter_text.text().strip().lower()
        selected_type = self.filter_type_combo.currentData() or ""
        selected_task = self.filter_task_combo.currentData() or ""
        out = []
        for cost in costs:
            if selected_type and getattr(cost.cost_type, "value", "") != selected_type:
                continue
            if selected_task and getattr(cost, "task_id", None) != selected_task:
                continue
            if text:
                task_name = task_names.get(cost.task_id, "") if getattr(cost, "task_id", None) else ""
                hay = f"{cost.description} {task_name}".lower()
                if text not in hay:
                    continue
            out.append(cost)
        return out


__all__ = ["CostFiltersMixin"]
