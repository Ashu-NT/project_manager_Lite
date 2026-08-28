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

    def _set_cost_phasing(self, cost_phasing: FinancialsMap) -> None:
        if cost_phasing == self._cost_phasing:
            return
        self._cost_phasing = cost_phasing
        self.costPhasingChanged.emit()

    def _set_cost_phasing_basis(self, value: FinancialsMap) -> None:
        if value != self._cost_phasing_basis:
            self._cost_phasing_basis = value
            self.costPhasingBasisChanged.emit()

    def _set_evm_basis(self, value: FinancialsMap) -> None:
        if value != self._evm_basis:
            self._evm_basis = value
            self.evmBasisChanged.emit()

    def _set_evm_metrics(self, value: FinancialsMap) -> None:
        if value != self._evm_metrics:
            self._evm_metrics = value
            self.evmMetricsChanged.emit()

    def _set_variance_metrics(self, value: FinancialsMap) -> None:
        if value != self._variance_metrics:
            self._variance_metrics = value
            self.varianceMetricsChanged.emit()

    def _set_report_definitions(self, value: FinancialsMap) -> None:
        if value != self._report_definitions:
            self._report_definitions = value
            self.reportDefinitionsChanged.emit()

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

    def _set_selected_change(self, value: FinancialsMap) -> None:
        if value != self._selected_change:
            self._selected_change = value
            self.selectedChangeChanged.emit()

    def _set_financial_changes(self, value: FinancialsMap) -> None:
        if value != self._financial_changes:
            self._financial_changes = value
            self._financial_changes_table_model.set_rows(value.get("items", []))
            self.financialChangesChanged.emit()

    def _set_financial_change_impacts(self, value: FinancialsMap) -> None:
        if value != self._financial_change_impacts:
            self._financial_change_impacts = value
            self._financial_change_impacts_table_model.set_rows(value.get("items", []))
            self.financialChangeImpactsChanged.emit()

    def _set_financial_change_query_state(self, state) -> None:
        change_order = (
            Qt.DescendingOrder.value
            if state.change_sort_direction == "desc"
            else Qt.AscendingOrder.value
        )
        impact_order = (
            Qt.DescendingOrder.value
            if state.impact_sort_direction == "desc"
            else Qt.AscendingOrder.value
        )
        if state.change_sort_key != self._change_sort_key:
            self._change_sort_key = state.change_sort_key
            self.changeSortKeyChanged.emit()
        if change_order != self._change_sort_direction:
            self._change_sort_direction = change_order
            self.changeSortDirectionChanged.emit()
        if state.impact_sort_key != self._impact_sort_key:
            self._impact_sort_key = state.impact_sort_key
            self.impactSortKeyChanged.emit()
        if impact_order != self._impact_sort_direction:
            self._impact_sort_direction = impact_order
            self.impactSortDirectionChanged.emit()
        filters = (
            state.change_search,
            state.change_status,
            state.change_approval_status,
            state.change_applied_state,
            state.impact_search,
            state.impact_type,
            state.impact_applied_state,
        )
        current = (
            self._change_search,
            self._change_status,
            self._change_approval_status,
            self._change_applied_state,
            self._impact_search,
            self._impact_type,
            self._impact_applied_state,
        )
        if filters != current:
            (
                self._change_search,
                self._change_status,
                self._change_approval_status,
                self._change_applied_state,
                self._impact_search,
                self._impact_type,
                self._impact_applied_state,
            ) = filters
            self.changeFiltersChanged.emit()

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
            self._billing_schedule_table_model.set_rows(value.get("items", []))
            self.billingScheduleChanged.emit()

    def _set_billing_preparations(self, value: FinancialsMap) -> None:
        if value != self._billing_preparations:
            self._billing_preparations = value
            self._billing_preparations_table_model.set_rows(value.get("items", []))
            self.billingPreparationsChanged.emit()

    def _set_billing_preparation_lines(self, value: FinancialsMap) -> None:
        if value != self._billing_preparation_lines:
            self._billing_preparation_lines = value
            self._billing_preparation_lines_table_model.set_rows(value.get("items", []))
            self.billingPreparationLinesChanged.emit()

    def _set_selected_billing_preparation_id(self, value: str) -> None:
        if value != self._selected_billing_preparation_id:
            self._selected_billing_preparation_id = value
            self.selectedBillingPreparationIdChanged.emit()

    def _set_selected_billing_preparation(self, value: FinancialsMap) -> None:
        if value != self._selected_billing_preparation:
            self._selected_billing_preparation = value
            self.selectedBillingPreparationChanged.emit()

    def _set_billing_query_state(self, state) -> None:
        values = (
            state.billing_schedule_sort_key,
            Qt.DescendingOrder.value if state.billing_schedule_sort_direction == "desc" else Qt.AscendingOrder.value,
            state.billing_preparation_sort_key,
            Qt.DescendingOrder.value if state.billing_preparation_sort_direction == "desc" else Qt.AscendingOrder.value,
            state.billing_line_sort_key,
            Qt.DescendingOrder.value if state.billing_line_sort_direction == "desc" else Qt.AscendingOrder.value,
            state.billing_schedule_search,
            state.billing_schedule_status,
            state.billing_schedule_source_state,
            state.billing_preparation_search,
            state.billing_preparation_status,
            state.billing_preparation_method,
            state.billing_preparation_approval_status,
            state.billing_preparation_delivery_state,
            state.billing_preparation_correction_state,
            state.billing_line_search,
            state.billing_line_source_type,
            state.billing_line_source_state,
        )
        current = (
            self._billing_schedule_sort_key,
            self._billing_schedule_sort_direction,
            self._billing_preparation_sort_key,
            self._billing_preparation_sort_direction,
            self._billing_line_sort_key,
            self._billing_line_sort_direction,
            self._billing_schedule_search,
            self._billing_schedule_status,
            self._billing_schedule_source_state,
            self._billing_preparation_search,
            self._billing_preparation_status,
            self._billing_preparation_method,
            self._billing_preparation_approval_status,
            self._billing_preparation_delivery_state,
            self._billing_preparation_correction_state,
            self._billing_line_search,
            self._billing_line_source_type,
            self._billing_line_source_state,
        )
        if values != current:
            (
                self._billing_schedule_sort_key,
                self._billing_schedule_sort_direction,
                self._billing_preparation_sort_key,
                self._billing_preparation_sort_direction,
                self._billing_line_sort_key,
                self._billing_line_sort_direction,
                self._billing_schedule_search,
                self._billing_schedule_status,
                self._billing_schedule_source_state,
                self._billing_preparation_search,
                self._billing_preparation_status,
                self._billing_preparation_method,
                self._billing_preparation_approval_status,
                self._billing_preparation_delivery_state,
                self._billing_preparation_correction_state,
                self._billing_line_search,
                self._billing_line_source_type,
                self._billing_line_source_state,
            ) = values
            self.billingQueryStateChanged.emit()

    def _set_commercial_projection(self, value: FinancialsMap) -> None:
        if value != self._commercial_projection:
            self._commercial_projection = value
            self.commercialProjectionChanged.emit()


__all__ = ["FinancialsStateMixin"]
