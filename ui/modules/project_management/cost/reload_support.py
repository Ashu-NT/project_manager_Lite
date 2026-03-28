from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.modules.project_management.domain.enums import CostType
from ui.platform.shared.styles.formatting import currency_symbol_from_code, fmt_currency


@dataclass(slots=True)
class CostReloadSnapshot:
    project_id: str
    costs: list[object]
    total_planned: float
    total_committed: float
    total_actual: float
    budget: float
    remaining: float | None
    source_breakdown: object | None
    labor_details: list[object]
    manual_labor_exists: bool


def build_cost_reload_snapshot(view, project_id: str, *, cost_service, reporting_service) -> CostReloadSnapshot:
    costs = cost_service.list_cost_items_for_project(project_id)
    budget = float(getattr(view._current_project, "planned_budget", 0.0) or 0.0)
    source_breakdown = None
    try:
        totals = reporting_service.get_project_cost_control_totals(project_id)
        source_breakdown = reporting_service.get_project_cost_source_breakdown(project_id)
        budget = float(getattr(totals, "budget", budget) or budget)
        total_planned = float(getattr(totals, "planned", 0.0) or 0.0)
        total_committed = float(getattr(totals, "committed", 0.0) or 0.0)
        total_actual = float(getattr(totals, "actual", 0.0) or 0.0)
        remaining = getattr(totals, "available", None)
    except Exception:
        total_planned = sum(float(cost.planned_amount or 0.0) for cost in costs)
        total_committed = sum(float(cost.committed_amount or 0.0) for cost in costs)
        total_actual = sum(float(cost.actual_amount or 0.0) for cost in costs)
        remaining = (budget - max(total_actual, total_committed)) if budget > 0 else None
    labor_details = reporting_service.get_project_labor_details(project_id)
    manual_labor_exists = any(getattr(cost, "cost_type", None) == CostType.LABOR for cost in costs)
    return CostReloadSnapshot(
        project_id=project_id,
        costs=list(costs),
        total_planned=total_planned,
        total_committed=total_committed,
        total_actual=total_actual,
        budget=budget,
        remaining=remaining,
        source_breakdown=source_breakdown,
        labor_details=list(labor_details),
        manual_labor_exists=manual_labor_exists,
    )


def apply_cost_reload_snapshot(view, snapshot: CostReloadSnapshot | None, *, preferred_cost_id: Optional[str] = None) -> None:
    project_id = view._current_project_id()
    if not project_id or snapshot is None or snapshot.project_id != project_id:
        clear_cost_view(view)
        if callable(sync := getattr(view, "_sync_cost_actions", None)):
            sync()
        return

    task_names = {task.id: task.name for task in view._project_tasks}
    tasks_by_id = {task.id: task for task in view._project_tasks}
    view.model.set_context(tasks_by_id, view._current_project.currency if view._current_project else "")

    currency = ((getattr(view._current_project, "currency", "") or "").upper() if view._current_project else "")
    symbol = currency_symbol_from_code(currency)
    view.lbl_kpi_budget.setText(fmt_currency(snapshot.budget, symbol) if snapshot.budget > 0 else "-")
    view.lbl_kpi_planned.setText(fmt_currency(snapshot.total_planned, symbol))
    view.lbl_kpi_committed.setText(fmt_currency(snapshot.total_committed, symbol))
    view.lbl_kpi_actual.setText(fmt_currency(snapshot.total_actual, symbol))
    view.lbl_kpi_remaining.setText(fmt_currency(snapshot.remaining, symbol) if snapshot.remaining is not None else "-")

    filtered_costs = view._apply_cost_filters(costs=snapshot.costs, task_names=task_names)
    view.model.set_costs(filtered_costs, task_names)
    if preferred_cost_id:
        select_cost_by_id(view, preferred_cost_id)
    elif filtered_costs:
        view.table.selectRow(0)
    else:
        view.table.clearSelection()

    if callable(updater := getattr(view, "_update_cost_header_badges", None)):
        updater(len(filtered_costs), len(snapshot.costs))
    view.lbl_costs_summary.setText(_cost_summary_text(snapshot, symbol, filtered_count=len(filtered_costs)))
    try:
        view.reload_labor_summary(
            project_id,
            details=snapshot.labor_details,
            manual_labor_exists=snapshot.manual_labor_exists,
        )
    except Exception as exc:
        view.tbl_labor_summary.setRowCount(0)
        view.lbl_labor_note.setText(f"Labor summary unavailable: {exc}")
    if callable(sync := getattr(view, "_sync_cost_actions", None)):
        sync()


def clear_cost_view(view) -> None:
    view.model.set_costs([], {})
    view.table.clearSelection()
    view.tbl_labor_summary.setRowCount(0)
    view.lbl_costs_summary.setText("")
    view.lbl_labor_note.setText("")
    view.lbl_kpi_budget.setText("-")
    view.lbl_kpi_planned.setText("-")
    view.lbl_kpi_committed.setText("-")
    view.lbl_kpi_actual.setText("-")
    view.lbl_kpi_remaining.setText("-")


def select_cost_by_id(view, cost_id: str) -> None:
    for row in range(view.model.rowCount()):
        item = view.model.get_cost(row)
        if item and item.id == cost_id:
            view.table.selectRow(row)
            return


def _cost_summary_text(snapshot: CostReloadSnapshot, symbol: str, *, filtered_count: int) -> str:
    summary = f"Showing {filtered_count} of {len(snapshot.costs)} cost item(s)."
    if snapshot.budget > 0 and snapshot.total_planned > snapshot.budget + 1e-9:
        summary = (
            f"Budget warning: Planned {fmt_currency(snapshot.total_planned, symbol)} is above budget "
            f"{fmt_currency(snapshot.budget, symbol)}.  {summary}"
        )
    if snapshot.source_breakdown and snapshot.source_breakdown.rows:
        actuals = {row.source_key: float(row.actual or 0.0) for row in snapshot.source_breakdown.rows}
        summary += (
            "  Actual sources: Direct Cost {0:.2f}, Computed Labor {1:.2f}, "
            "Labor Adjustment {2:.2f}.".format(
                actuals.get("DIRECT_COST", 0.0),
                actuals.get("COMPUTED_LABOR", 0.0),
                actuals.get("LABOR_ADJUSTMENT", 0.0),
            )
        )
    return summary


__all__ = [
    "CostReloadSnapshot",
    "apply_cost_reload_snapshot",
    "build_cost_reload_snapshot",
    "clear_cost_view",
]


def reload_project_combo(view, *, preferred_project_id: Optional[str] = None) -> list[object]:
    projects = view._project_service.list_projects()
    view.project_combo.blockSignals(True)
    view.project_combo.clear()
    for project in projects:
        view.project_combo.addItem(project.name, userData=project.id)
    view.project_combo.blockSignals(False)
    if preferred_project_id and (index := view.project_combo.findData(preferred_project_id)) != -1:
        view.project_combo.setCurrentIndex(index)
    elif view.project_combo.count() > 0:
        view.project_combo.setCurrentIndex(0)
    return projects
