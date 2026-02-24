from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QComboBox, QLabel, QLineEdit, QTableWidget

from core.models import Project, Task
from core.services.cost import CostService
from core.services.project import ProjectService
from core.services.reporting import ReportingService
from core.services.task import TaskService
from ui.cost.filters import CostFiltersMixin
from ui.cost.models import CostTableModel
from ui.styles.formatting import currency_symbol_from_code, fmt_currency


class CostProjectFlowMixin(CostFiltersMixin):
    project_combo: QComboBox
    filter_text: QLineEdit
    filter_type_combo: QComboBox
    filter_task_combo: QComboBox
    model: CostTableModel
    tbl_labor_summary: QTableWidget
    lbl_labor_note: QLabel
    lbl_costs_summary: QLabel
    lbl_kpi_budget: QLabel
    lbl_kpi_planned: QLabel
    lbl_kpi_committed: QLabel
    lbl_kpi_actual: QLabel
    lbl_kpi_remaining: QLabel
    _project_service: ProjectService
    _task_service: TaskService
    _cost_service: CostService
    _reporting_service: ReportingService
    _current_project: Project | None
    _project_tasks: list[Task]

    def _load_projects(self):
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        projects = self._project_service.list_projects()
        for p in projects:
            self.project_combo.addItem(p.name, userData=p.id)
        self.project_combo.blockSignals(False)
        self._reload_cost_type_filter_options()

        if self.project_combo.count() > 0:
            self.project_combo.setCurrentIndex(0)
            self._on_project_changed(0)

    def _on_costs_or_tasks_changed(self, project_id: str):
        pid = self._current_project_id()
        if pid != project_id:
            return
        self._project_tasks = self._task_service.list_tasks_for_project(pid)
        self._current_project = self._project_service.get_project(pid)
        self._reload_task_filter_options()
        self.reload_costs()

    def _on_project_changed_event(self, project_id: str):
        prev_pid = self._current_project_id()
        projects = self._project_service.list_projects()
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for p in projects:
            self.project_combo.addItem(p.name, userData=p.id)
        self.project_combo.blockSignals(False)
        if prev_pid and prev_pid in [p.id for p in projects]:
            idx = self.project_combo.findData(prev_pid)
            if idx != -1:
                self.project_combo.setCurrentIndex(idx)
        else:
            if self.project_combo.count() > 0:
                self.project_combo.setCurrentIndex(0)
        pid = self._current_project_id()
        self._current_project = self._project_service.get_project(pid) if pid else None
        self._project_tasks = self._task_service.list_tasks_for_project(pid) if pid else []
        self._reload_cost_type_filter_options()
        self._reload_task_filter_options()
        self.reload_costs()

    def _on_resources_changed(self, _resource_id: str) -> None:
        pid = self._current_project_id()
        if not pid:
            return
        self.reload_costs()

    def _current_project_id(self) -> Optional[str]:
        idx = self.project_combo.currentIndex()
        if idx < 0:
            return None
        return self.project_combo.itemData(idx)

    def _load_tasks_for_current_project(self):
        pid = self._current_project_id()
        if not pid:
            self._project_tasks = []
            return
        self._project_tasks = self._task_service.list_tasks_for_project(pid)

    def _on_project_changed(self, index: int):
        pid = self._current_project_id()
        if not pid:
            self._current_project = None
            self._project_tasks = []
            self.model.set_costs([], {})
            self._reload_task_filter_options()
            self.lbl_costs_summary.setText("")
            self.lbl_kpi_budget.setText("-")
            self.lbl_kpi_planned.setText("-")
            self.lbl_kpi_committed.setText("-")
            self.lbl_kpi_actual.setText("-")
            self.lbl_kpi_remaining.setText("-")
            return
        projects = self._project_service.list_projects()
        self._current_project = next((p for p in projects if p.id == pid), None)
        self._load_tasks_for_current_project()
        self._reload_cost_type_filter_options()
        self._reload_task_filter_options()
        tasks_by_id = {t.id: t for t in self._project_tasks}
        project_currency = self._current_project.currency if self._current_project else ""
        self.model.set_context(tasks_by_id, project_currency)

        self.reload_costs()

    def reload_costs(self):
        pid = self._current_project_id()
        if not pid:
            self.model.set_costs([], {})
            self.tbl_labor_summary.setRowCount(0)
            self.lbl_costs_summary.setText("")
            self.lbl_labor_note.setText("")
            self.lbl_kpi_budget.setText("-")
            self.lbl_kpi_planned.setText("-")
            self.lbl_kpi_committed.setText("-")
            self.lbl_kpi_actual.setText("-")
            self.lbl_kpi_remaining.setText("-")
            return

        costs = self._cost_service.list_cost_items_for_project(pid)
        task_names = {t.id: t.name for t in self._project_tasks}

        tasks_by_id = {t.id: t for t in self._project_tasks}
        project_currency = self._current_project.currency if self._current_project else ""
        self.model.set_context(tasks_by_id, project_currency)

        self.model.set_costs(costs, task_names)

        cur = (
            (getattr(self._current_project, "currency", "") or "").upper()
            if self._current_project
            else ""
        )
        sym = currency_symbol_from_code(cur)
        budget = float(getattr(self._current_project, "planned_budget", 0.0) or 0.0)
        total_planned = sum(float(c.planned_amount or 0.0) for c in costs)
        total_committed = sum(float(c.committed_amount or 0.0) for c in costs)
        total_actual = sum(float(c.actual_amount or 0.0) for c in costs)
        exposure = max(total_actual, total_committed)
        remaining = (budget - exposure) if budget > 0 else None

        self.lbl_kpi_budget.setText(fmt_currency(budget, sym) if budget > 0 else "-")
        self.lbl_kpi_planned.setText(fmt_currency(total_planned, sym))
        self.lbl_kpi_committed.setText(fmt_currency(total_committed, sym))
        self.lbl_kpi_actual.setText(fmt_currency(total_actual, sym))
        self.lbl_kpi_remaining.setText(
            fmt_currency(remaining, sym) if remaining is not None else "-"
        )

        filtered_costs = self._apply_cost_filters(costs=costs, task_names=task_names)
        self.model.set_costs(filtered_costs, task_names)
        self.lbl_costs_summary.setText(
            f"Showing {len(filtered_costs)} of {len(costs)} cost item(s)."
        )

        try:
            self.reload_labor_summary(pid)
        except Exception as exc:
            self.tbl_labor_summary.setRowCount(0)
            self.lbl_labor_note.setText(f"Labor summary unavailable: {exc}")
