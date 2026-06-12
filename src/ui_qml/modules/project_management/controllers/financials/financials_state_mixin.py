from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.financials.financials_types import (
    FinancialsMap,
    FinancialsObjectList,
)


class FinancialsStateMixin:
    def _set_overview(self, overview: FinancialsMap) -> None:
        if overview == self._overview:
            return
        self._overview = overview
        self.overviewChanged.emit()

    def _set_project_options(self, project_options: FinancialsObjectList) -> None:
        if project_options == self._project_options:
            return
        self._project_options = project_options
        self.projectOptionsChanged.emit()

    def _set_cost_type_options(self, cost_type_options: FinancialsObjectList) -> None:
        if cost_type_options == self._cost_type_options:
            return
        self._cost_type_options = cost_type_options
        self.costTypeOptionsChanged.emit()

    def _set_task_options(self, task_options: FinancialsObjectList) -> None:
        if task_options == self._task_options:
            return
        self._task_options = task_options
        self.taskOptionsChanged.emit()

    def _set_selected_project_id(self, selected_project_id: str) -> None:
        if selected_project_id == self._selected_project_id:
            return
        self._selected_project_id = selected_project_id
        self.selectedProjectIdChanged.emit()

    def _set_selected_cost_type(self, selected_cost_type: str) -> None:
        if selected_cost_type == self._selected_cost_type:
            return
        self._selected_cost_type = selected_cost_type
        self.selectedCostTypeChanged.emit()

    def _set_search_text(self, search_text: str) -> None:
        if search_text == self._search_text:
            return
        self._search_text = search_text
        self.searchTextChanged.emit()

    def _set_costs(self, costs: FinancialsMap) -> None:
        if costs == self._costs:
            return
        self._costs = costs
        self._costs_table_model.set_rows(costs.get("items", []))
        self.costsChanged.emit()

    def _set_selected_cost(self, selected_cost: FinancialsMap) -> None:
        if selected_cost == self._selected_cost:
            return
        self._selected_cost = selected_cost
        self.selectedCostChanged.emit()

    def _set_selected_cost_id(self, selected_cost_id: str) -> None:
        if selected_cost_id == self._selected_cost_id:
            return
        self._selected_cost_id = selected_cost_id
        self.selectedCostIdChanged.emit()

    def _set_cashflow(self, cashflow: FinancialsMap) -> None:
        if cashflow == self._cashflow:
            return
        self._cashflow = cashflow
        self.cashflowChanged.emit()

    def _set_ledger(self, ledger: FinancialsMap) -> None:
        if ledger == self._ledger:
            return
        self._ledger = ledger
        self._ledger_table_model.set_rows(ledger.get("items", []))
        self.ledgerChanged.emit()

    def _set_source_analytics(self, source_analytics: FinancialsMap) -> None:
        if source_analytics == self._source_analytics:
            return
        self._source_analytics = source_analytics
        self.sourceAnalyticsChanged.emit()

    def _set_cost_type_analytics(self, cost_type_analytics: FinancialsMap) -> None:
        if cost_type_analytics == self._cost_type_analytics:
            return
        self._cost_type_analytics = cost_type_analytics
        self.costTypeAnalyticsChanged.emit()

    def _set_notes(self, notes: list[str]) -> None:
        if notes == self._notes:
            return
        self._notes = notes
        self.notesChanged.emit()

    def _set_cost_page(self, value: int) -> None:
        if value == self._cost_page:
            return
        self._cost_page = value
        self.costPageChanged.emit()

    def _set_cost_page_size(self, value: int) -> None:
        if value == self._cost_page_size:
            return
        self._cost_page_size = value
        self.costPageSizeChanged.emit()

    def _set_cost_total_count(self, value: int) -> None:
        if value == self._cost_total_count:
            return
        self._cost_total_count = value
        self.costTotalCountChanged.emit()

    def _set_selected_cost_ids(self, ids: list[str]) -> None:
        if ids == self._selected_cost_ids:
            return
        self._selected_cost_ids = ids
        self.selectedCostIdsChanged.emit()
        self.selectedCostCountChanged.emit()

    def _set_forecast(self, forecast: FinancialsMap) -> None:
        if forecast == self._forecast:
            return
        self._forecast = forecast
        self.forecastChanged.emit()

    def _set_commitment_summary(self, summary: FinancialsMap) -> None:
        if summary == self._commitment_summary:
            return
        self._commitment_summary = summary
        self.commitmentSummaryChanged.emit()

    def _set_baseline_variance(self, rows: FinancialsObjectList) -> None:
        if rows == self._baseline_variance:
            return
        self._baseline_variance = rows
        self.baselineVarianceChanged.emit()


__all__ = ["FinancialsStateMixin"]
