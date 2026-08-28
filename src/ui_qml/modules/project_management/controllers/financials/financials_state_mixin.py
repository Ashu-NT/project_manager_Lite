from __future__ import annotations

from PySide6.QtCore import Qt

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

    def _set_activity(self, activity: FinancialsMap) -> None:
        if activity == self._activity:
            return
        self._activity = activity
        self.activityChanged.emit()

    def _set_actual_sort_state(self, key: str, direction: str) -> None:
        normalized_direction = (
            Qt.DescendingOrder.value if direction == "desc" else Qt.AscendingOrder.value
        )
        if key != self._actual_sort_key:
            self._actual_sort_key = key
            self.actualSortKeyChanged.emit()
        if normalized_direction != self._actual_sort_direction:
            self._actual_sort_direction = normalized_direction
            self.actualSortDirectionChanged.emit()

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

    def _set_selected_forecast_id(self, value: str) -> None:
        if value != self._selected_forecast_id:
            self._selected_forecast_id = value
            self.selectedForecastIdChanged.emit()

    def _set_forecast_versions(self, value: FinancialsMap) -> None:
        if value != self._forecast_versions:
            self._forecast_versions = value
            self._forecast_versions_table_model.set_rows(value.get("items", []))
            self.forecastVersionsChanged.emit()

    def _set_forecast_lines(self, value: FinancialsMap) -> None:
        if value != self._forecast_lines:
            self._forecast_lines = value
            self._forecast_lines_table_model.set_rows(value.get("items", []))
            self.forecastLinesChanged.emit()

    def _set_selected_forecast(self, value: FinancialsMap) -> None:
        if value != self._selected_forecast:
            self._selected_forecast = value
            self.selectedForecastChanged.emit()

    def _set_forecast_query_state(self, state) -> None:
        version_order = (
            Qt.DescendingOrder.value
            if state.forecast_version_sort_direction == "desc"
            else Qt.AscendingOrder.value
        )
        line_order = (
            Qt.DescendingOrder.value
            if state.forecast_line_sort_direction == "desc"
            else Qt.AscendingOrder.value
        )
        if state.forecast_version_sort_key != self._forecast_version_sort_key:
            self._forecast_version_sort_key = state.forecast_version_sort_key
            self.forecastVersionSortKeyChanged.emit()
        if version_order != self._forecast_version_sort_direction:
            self._forecast_version_sort_direction = version_order
            self.forecastVersionSortDirectionChanged.emit()
        if state.forecast_line_sort_key != self._forecast_line_sort_key:
            self._forecast_line_sort_key = state.forecast_line_sort_key
            self.forecastLineSortKeyChanged.emit()
        if line_order != self._forecast_line_sort_direction:
            self._forecast_line_sort_direction = line_order
            self.forecastLineSortDirectionChanged.emit()
        filters = (
            state.forecast_version_search,
            state.forecast_version_status,
            state.forecast_generation_mode,
            state.forecast_line_search,
            state.forecast_line_source_type,
        )
        current = (
            self._forecast_version_search,
            self._forecast_version_status,
            self._forecast_generation_mode,
            self._forecast_line_search,
            self._forecast_line_source_type,
        )
        if filters != current:
            (
                self._forecast_version_search,
                self._forecast_version_status,
                self._forecast_generation_mode,
                self._forecast_line_search,
                self._forecast_line_source_type,
            ) = filters
            self.forecastFiltersChanged.emit()

    def _set_selected_change_id(self, value: str) -> None:
        if value != self._selected_change_id:
            self._selected_change_id = value
            self.selectedChangeIdChanged.emit()

    def _set_financial_changes(self, value: FinancialsMap) -> None:
        if value != self._financial_changes:
            self._financial_changes = value
            self.financialChangesChanged.emit()

    def _set_financial_change_impacts(self, value: FinancialsMap) -> None:
        if value != self._financial_change_impacts:
            self._financial_change_impacts = value
            self.financialChangeImpactsChanged.emit()

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

    def _set_commitment_sort_state(self, key: str, direction: str) -> None:
        normalized_direction = (
            Qt.DescendingOrder.value if direction == "desc" else Qt.AscendingOrder.value
        )
        if key != self._commitment_sort_key:
            self._commitment_sort_key = key
            self.commitmentSortKeyChanged.emit()
        if normalized_direction != self._commitment_sort_direction:
            self._commitment_sort_direction = normalized_direction
            self.commitmentSortDirectionChanged.emit()

    def _set_baseline_variance(self, rows: FinancialsObjectList) -> None:
        if rows == self._baseline_variance:
            return
        self._baseline_variance = rows
        self.baselineVarianceChanged.emit()

    def _set_selected_baseline_id(self, value: str) -> None:
        if value != self._selected_baseline_id:
            self._selected_baseline_id = value
            self.selectedBaselineIdChanged.emit()

    def _set_baseline_versions(self, value: FinancialsMap) -> None:
        if value != self._baseline_versions:
            self._baseline_versions = value
            self.baselineVersionsChanged.emit()

    def _set_variance_basis(self, value: FinancialsMap) -> None:
        if value != self._variance_basis:
            self._variance_basis = value
            self.varianceBasisChanged.emit()

    def _set_report_basis(self, value: FinancialsMap) -> None:
        if value != self._report_basis:
            self._report_basis = value
            self.reportBasisChanged.emit()

    def _set_financial_profile(self, value: FinancialsMap) -> None:
        if value != self._financial_profile:
            self._financial_profile = value
            self.financialProfileChanged.emit()

    def _set_budget_versions(self, value: FinancialsMap) -> None:
        if value != self._budget_versions:
            self._budget_versions = value
            self._budget_versions_table_model.set_rows(value.get("items", []))
            self.budgetVersionsChanged.emit()

    def _set_budget_lines(self, value: FinancialsMap) -> None:
        if value != self._budget_lines:
            self._budget_lines = value
            self._budget_lines_table_model.set_rows(value.get("items", []))
            self.budgetLinesChanged.emit()

    def _set_selected_budget_id(self, value: str) -> None:
        if value != self._selected_budget_id:
            self._selected_budget_id = value
            self.selectedBudgetIdChanged.emit()

    def _set_budget_sort_state(
        self,
        *,
        version_key: str,
        version_direction: str,
        line_key: str,
        line_direction: str,
    ) -> None:
        version_order = (
            Qt.DescendingOrder.value
            if version_direction == "desc"
            else Qt.AscendingOrder.value
        )
        line_order = (
            Qt.DescendingOrder.value
            if line_direction == "desc"
            else Qt.AscendingOrder.value
        )
        if version_key != self._budget_version_sort_key:
            self._budget_version_sort_key = version_key
            self.budgetVersionSortKeyChanged.emit()
        if version_order != self._budget_version_sort_direction:
            self._budget_version_sort_direction = version_order
            self.budgetVersionSortDirectionChanged.emit()
        if line_key != self._budget_line_sort_key:
            self._budget_line_sort_key = line_key
            self.budgetLineSortKeyChanged.emit()
        if line_order != self._budget_line_sort_direction:
            self._budget_line_sort_direction = line_order
            self.budgetLineSortDirectionChanged.emit()

    def _set_rate_cards(self, value: FinancialsMap) -> None:
        if value != self._rate_cards:
            self._rate_cards = value
            self._rate_cards_table_model.set_rows(value.get("items", []))
            self.rateCardsChanged.emit()

    def _set_rate_lines(self, value: FinancialsMap) -> None:
        if value != self._rate_lines:
            self._rate_lines = value
            self._rate_lines_table_model.set_rows(value.get("items", []))
            self.rateLinesChanged.emit()

    def _set_selected_rate_card_id(self, value: str) -> None:
        if value != self._selected_rate_card_id:
            self._selected_rate_card_id = value
            self.selectedRateCardIdChanged.emit()

    def _set_selected_rate_card(self, value: FinancialsMap) -> None:
        if value != self._selected_rate_card:
            self._selected_rate_card = value
            self.selectedRateCardChanged.emit()

    def _set_rate_query_state(self, state) -> None:
        card_order = (
            Qt.DescendingOrder.value
            if state.rate_card_sort_direction == "desc"
            else Qt.AscendingOrder.value
        )
        line_order = (
            Qt.DescendingOrder.value
            if state.rate_line_sort_direction == "desc"
            else Qt.AscendingOrder.value
        )
        if state.rate_card_sort_key != self._rate_card_sort_key:
            self._rate_card_sort_key = state.rate_card_sort_key
            self.rateCardSortKeyChanged.emit()
        if card_order != self._rate_card_sort_direction:
            self._rate_card_sort_direction = card_order
            self.rateCardSortDirectionChanged.emit()
        if state.rate_line_sort_key != self._rate_line_sort_key:
            self._rate_line_sort_key = state.rate_line_sort_key
            self.rateLineSortKeyChanged.emit()
        if line_order != self._rate_line_sort_direction:
            self._rate_line_sort_direction = line_order
            self.rateLineSortDirectionChanged.emit()
        filters = (
            state.rate_card_search,
            state.rate_card_scope,
            state.rate_card_status,
            state.rate_line_search,
            state.rate_line_rate_type,
            state.rate_line_status,
            state.rate_line_effective_status,
        )
        current = (
            self._rate_card_search,
            self._rate_card_scope,
            self._rate_card_status,
            self._rate_line_search,
            self._rate_line_rate_type,
            self._rate_line_status,
            self._rate_line_effective_status,
        )
        if filters != current:
            (
                self._rate_card_search,
                self._rate_card_scope,
                self._rate_card_status,
                self._rate_line_search,
                self._rate_line_rate_type,
                self._rate_line_status,
                self._rate_line_effective_status,
            ) = filters
            self.rateFiltersChanged.emit()

    def _set_planned_cost_versions(self, value: FinancialsMap) -> None:
        if value != self._planned_cost_versions:
            self._planned_cost_versions = value
            self._planned_cost_versions_table_model.set_rows(value.get("items", []))
            self.plannedCostVersionsChanged.emit()

    def _set_planned_cost_lines(self, value: FinancialsMap) -> None:
        if value != self._planned_cost_lines:
            self._planned_cost_lines = value
            self._planned_cost_lines_table_model.set_rows(value.get("items", []))
            self.plannedCostLinesChanged.emit()

    def _set_selected_planned_cost_version_id(self, value: str) -> None:
        if value != self._selected_planned_cost_version_id:
            self._selected_planned_cost_version_id = value
            self.selectedPlannedCostVersionIdChanged.emit()

    def _set_planned_cost_sort_state(
        self,
        *,
        version_key: str,
        version_direction: str,
        line_key: str,
        line_direction: str,
    ) -> None:
        version_order = (
            Qt.DescendingOrder.value
            if version_direction == "desc"
            else Qt.AscendingOrder.value
        )
        line_order = (
            Qt.DescendingOrder.value
            if line_direction == "desc"
            else Qt.AscendingOrder.value
        )
        if version_key != self._planned_cost_version_sort_key:
            self._planned_cost_version_sort_key = version_key
            self.plannedCostVersionSortKeyChanged.emit()
        if version_order != self._planned_cost_version_sort_direction:
            self._planned_cost_version_sort_direction = version_order
            self.plannedCostVersionSortDirectionChanged.emit()
        if line_key != self._planned_cost_line_sort_key:
            self._planned_cost_line_sort_key = line_key
            self.plannedCostLineSortKeyChanged.emit()
        if line_order != self._planned_cost_line_sort_direction:
            self._planned_cost_line_sort_direction = line_order
            self.plannedCostLineSortDirectionChanged.emit()

    def _set_billing_profile(self, value: FinancialsMap) -> None:
        if value != self._billing_profile:
            self._billing_profile = value
            self.billingProfileChanged.emit()

    def _set_billing_schedule(self, value: FinancialsMap) -> None:
        if value != self._billing_schedule:
            self._billing_schedule = value
            self.billingScheduleChanged.emit()

    def _set_billing_preparations(self, value: FinancialsMap) -> None:
        if value != self._billing_preparations:
            self._billing_preparations = value
            self.billingPreparationsChanged.emit()

    def _set_commercial_projection(self, value: FinancialsMap) -> None:
        if value != self._commercial_projection:
            self._commercial_projection = value
            self.commercialProjectionChanged.emit()


__all__ = ["FinancialsStateMixin"]
