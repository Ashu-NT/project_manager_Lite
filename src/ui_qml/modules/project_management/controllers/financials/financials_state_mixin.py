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

    def _set_task_options(self, task_options: FinancialsObjectList) -> None:
        if task_options == self._task_options:
            return
        self._task_options = task_options
        self.taskOptionsChanged.emit()

    def _set_manual_actual_options(self, options: FinancialsMap) -> None:
        if options == self._manual_actual_options:
            return
        self._manual_actual_options = options
        self.manualActualOptionsChanged.emit()

    def _set_selected_project_id(self, selected_project_id: str) -> None:
        if selected_project_id == self._selected_project_id:
            return
        self._selected_project_id = selected_project_id
        self.selectedProjectIdChanged.emit()

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

    def _set_commitments(self, commitments: FinancialsMap) -> None:
        if commitments == self._commitments:
            return
        self._commitments = commitments
        self._commitments_table_model.set_rows(commitments.get("items", []))
        self.commitmentsChanged.emit()

    def _set_baseline_variance(self, rows: FinancialsObjectList) -> None:
        if rows == self._baseline_variance:
            return
        self._baseline_variance = rows
        self.baselineVarianceChanged.emit()

    def _set_financial_profile(self, value: FinancialsMap) -> None:
        if value != self._financial_profile:
            self._financial_profile = value
            self.financialProfileChanged.emit()

    def _set_budget_versions(self, value: FinancialsMap) -> None:
        if value != self._budget_versions:
            self._budget_versions = value
            self.budgetVersionsChanged.emit()

    def _set_budget_lines(self, value: FinancialsMap) -> None:
        if value != self._budget_lines:
            self._budget_lines = value
            self.budgetLinesChanged.emit()

    def _set_rate_cards(self, value: FinancialsMap) -> None:
        if value != self._rate_cards:
            self._rate_cards = value
            self.rateCardsChanged.emit()

    def _set_rate_lines(self, value: FinancialsMap) -> None:
        if value != self._rate_lines:
            self._rate_lines = value
            self.rateLinesChanged.emit()

    def _set_planned_cost_versions(self, value: FinancialsMap) -> None:
        if value != self._planned_cost_versions:
            self._planned_cost_versions = value
            self.plannedCostVersionsChanged.emit()

    def _set_planned_cost_lines(self, value: FinancialsMap) -> None:
        if value != self._planned_cost_lines:
            self._planned_cost_lines = value
            self.plannedCostLinesChanged.emit()


__all__ = ["FinancialsStateMixin"]
