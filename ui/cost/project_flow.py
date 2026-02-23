from __future__ import annotations

from typing import Optional

from core.models import CostType
from ui.styles.formatting import currency_symbol_from_code, fmt_currency


class CostProjectFlowMixin:
    def _load_projects(self):
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        projects = self._project_service.list_projects()
        for p in projects:
            self.project_combo.addItem(p.name, userData=p.id)
        self.project_combo.blockSignals(False)

        if self.project_combo.count() > 0:
            self.project_combo.setCurrentIndex(0)
            self._on_project_changed(0)

    def _on_costs_or_tasks_changed(self, project_id: str):
        pid = self._current_project_id()
        if pid != project_id:
            return
        self._project_tasks = self._task_service.list_tasks_for_project(pid)
        self._current_project = self._project_service.get_project(pid)
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
            return
        projects = self._project_service.list_projects()
        self._current_project = next((p for p in projects if p.id == pid), None)
        self._load_tasks_for_current_project()
        tasks_by_id = {t.id: t for t in self._project_tasks}
        project_currency = self._current_project.currency if self._current_project else ""
        self.model.set_context(tasks_by_id, project_currency)

        self.reload_costs()

    def reload_costs(self):
        pid = self._current_project_id()
        if not pid:
            self.model.set_costs([], {})
            self.tbl_labor_summary.setRowCount(0)
            self.lbl_labor_note.setText("")
            return

        costs = self._cost_service.list_cost_items_for_project(pid)
        task_names = {t.id: t.name for t in self._project_tasks}

        tasks_by_id = {t.id: t for t in self._project_tasks}
        project_currency = self._current_project.currency if self._current_project else ""
        self.model.set_context(tasks_by_id, project_currency)

        self.model.set_costs(costs, task_names)

        try:
            row = self._reporting_service.get_cost_breakdown(pid)
            planed_total = sum(float(r.planned or 0.0) for r in row)
            actual_total = sum(float(r.actual or 0.0) for r in row)

            budget = float(getattr(self._current_project, "planned_budget", 0.0) or 0.0)
            cur = (
                (getattr(self._current_project, "currency", "") or "").upper()
                if self._current_project
                else ""
            )
            sym = currency_symbol_from_code(cur)

            rem_plan = budget - planed_total
            rem_actual = budget - actual_total

            lines = []
            if budget > 0:
                lines.append(f"Budget: {fmt_currency(budget, sym)}")
                lines.append(
                    f"Total Planned Cost: {fmt_currency(planed_total, sym)} (Remaining vs plan: {fmt_currency(rem_plan,sym)})"
                )
                lines.append(
                    f"Total Actual Cost: {fmt_currency(actual_total, sym)} (Remaining vs plan: {fmt_currency(rem_actual,sym)})"
                )
                if planed_total > budget:
                    lines.append("Planned total exceeds budget.")
            else:
                lines.append(f"Total Planned Cost: {fmt_currency(planed_total, sym)}")
                lines.append(f"Total Actual Cost: {fmt_currency(actual_total, sym)}")
                lines.append("Note: set project budget to track remaining budget.")

            self.lbl_budget_summary.setText("\n".join(lines))
        except Exception:
            self.lbl_budget_summary.setText("")

        try:
            self.reload_labor_summary(pid)
        except Exception:
            self.tbl_labor_summary.setRowCount(0)
            self.lbl_labor_note.setText("")
