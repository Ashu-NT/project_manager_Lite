from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.financials.financials_types import (
    default_collection,
    default_detail,
)


class FinancialsSelectionMixin:
    def _select_destination(self, destination: str) -> None:
        normalized = str(destination or "").strip().lower()
        if normalized not in self._finance_destinations:
            normalized = "overview"
        if normalized == self._active_destination:
            return
        self._active_destination = normalized
        self._active_subsection = self._finance_subsections[normalized][0]
        self.activeDestinationChanged.emit()
        self.activeSubsectionChanged.emit()
        self.refresh()

    def _select_subsection(self, subsection: str) -> None:
        allowed = self._finance_subsections[self._active_destination]
        normalized = str(subsection or "").strip().lower()
        if normalized not in allowed:
            normalized = allowed[0]
        if normalized == self._active_subsection:
            return
        self._active_subsection = normalized
        self.activeSubsectionChanged.emit()
        self.refresh()

    def _select_project(self, project_id: str) -> None:
        normalized_value = (project_id or "").strip()
        if normalized_value == self._selected_project_id:
            return
        self._set_selected_project_id(normalized_value)
        self._budget_line_page = 1
        self._budget_version_page = 1
        self._rate_line_page = 1
        self._rate_card_page = 1
        self._planned_cost_line_page = 1
        self._planned_cost_version_page = 1
        self._billing_preparation_page = 1
        self._actual_page = 1
        self._commitment_page = 1
        self._set_selected_forecast_id("")
        self._set_selected_rate_card_id("")
        self._set_selected_rate_card(default_detail())
        self._forecast_version_page = 1
        self._forecast_line_page = 1
        self._set_selected_budget_id("")
        self._set_selected_planned_cost_version_id("")
        self._set_selected_change_id("")
        self._set_selected_baseline_id("")
        self._reset_destination_state()
        self.refresh()

    def _select_forecast_version(self, forecast_id: str) -> None:
        value = (forecast_id or "").strip()
        if value != self._selected_forecast_id:
            self._set_selected_forecast_id(value)
            self._forecast_line_page = 1
            self._set_selected_forecast(default_detail())
            self._set_forecast_lines(default_collection())
            self.refresh()

    def _set_forecast_version_page(self, page: int) -> None:
        normalized = max(1, int(page))
        if normalized != self._forecast_version_page:
            self._forecast_version_page = normalized
            self.refresh()

    def _set_forecast_line_page(self, page: int) -> None:
        normalized = max(1, int(page))
        if normalized != self._forecast_line_page:
            self._forecast_line_page = normalized
            self.refresh()

    def _set_forecast_version_sort(self, key: str, direction: int) -> None:
        normalized_key = str(key or "").strip()
        if (
            normalized_key != self._forecast_version_sort_key
            or int(direction) != self._forecast_version_sort_direction
        ):
            self._forecast_version_sort_key = normalized_key
            self._forecast_version_sort_direction = int(direction)
            self._forecast_version_page = 1
            self.forecastVersionSortKeyChanged.emit()
            self.forecastVersionSortDirectionChanged.emit()
            self.refresh()

    def _set_forecast_line_sort(self, key: str, direction: int) -> None:
        normalized_key = str(key or "").strip()
        if (
            normalized_key != self._forecast_line_sort_key
            or int(direction) != self._forecast_line_sort_direction
        ):
            self._forecast_line_sort_key = normalized_key
            self._forecast_line_sort_direction = int(direction)
            self._forecast_line_page = 1
            self.forecastLineSortKeyChanged.emit()
            self.forecastLineSortDirectionChanged.emit()
            self.refresh()

    def _set_forecast_version_filters(
        self, search: str, status: str, generation_mode: str
    ) -> None:
        values = (
            str(search or "").strip(),
            str(status or "").strip().lower(),
            str(generation_mode or "").strip().lower(),
        )
        current = (
            self._forecast_version_search,
            self._forecast_version_status,
            self._forecast_generation_mode,
        )
        if values != current:
            (
                self._forecast_version_search,
                self._forecast_version_status,
                self._forecast_generation_mode,
            ) = values
            self._forecast_version_page = 1
            self.forecastFiltersChanged.emit()
            self.refresh()

    def _set_forecast_line_filters(self, search: str, source_type: str) -> None:
        values = (
            str(search or "").strip(),
            str(source_type or "").strip().lower(),
        )
        current = (self._forecast_line_search, self._forecast_line_source_type)
        if values != current:
            self._forecast_line_search, self._forecast_line_source_type = values
            self._forecast_line_page = 1
            self.forecastFiltersChanged.emit()
            self.refresh()

    def _select_budget_version(self, budget_id: str) -> None:
        value = (budget_id or "").strip()
        if value != self._selected_budget_id:
            self._set_selected_budget_id(value)
            self._budget_line_page = 1
            self.refresh()

    def _select_rate_card(self, rate_card_id: str) -> None:
        value = str(rate_card_id or "").strip()
        if value != self._selected_rate_card_id:
            self._set_selected_rate_card_id(value)
            self._rate_line_page = 1
            self._set_selected_rate_card(default_detail())
            self._set_rate_lines(default_collection())
            self.refresh()

    def _set_rate_card_page(self, page: int) -> None:
        normalized = max(1, int(page))
        if normalized != self._rate_card_page:
            self._rate_card_page = normalized
            self.refresh()

    def _set_rate_line_page(self, page: int) -> None:
        normalized = max(1, int(page))
        if normalized != self._rate_line_page:
            self._rate_line_page = normalized
            self.refresh()

    def _set_rate_card_sort(self, key: str, direction: int) -> None:
        normalized_key = str(key or "").strip()
        if (
            normalized_key != self._rate_card_sort_key
            or int(direction) != self._rate_card_sort_direction
        ):
            self._rate_card_sort_key = normalized_key
            self._rate_card_sort_direction = int(direction)
            self._rate_card_page = 1
            self.rateCardSortKeyChanged.emit()
            self.rateCardSortDirectionChanged.emit()
            self.refresh()

    def _set_rate_line_sort(self, key: str, direction: int) -> None:
        normalized_key = str(key or "").strip()
        if (
            normalized_key != self._rate_line_sort_key
            or int(direction) != self._rate_line_sort_direction
        ):
            self._rate_line_sort_key = normalized_key
            self._rate_line_sort_direction = int(direction)
            self._rate_line_page = 1
            self.rateLineSortKeyChanged.emit()
            self.rateLineSortDirectionChanged.emit()
            self.refresh()

    def _set_rate_card_filters(self, search: str, scope: str, status: str) -> None:
        values = (
            str(search or "").strip(),
            str(scope or "").strip().lower(),
            str(status or "").strip().lower(),
        )
        if values != (self._rate_card_search, self._rate_card_scope, self._rate_card_status):
            self._rate_card_search, self._rate_card_scope, self._rate_card_status = values
            self._rate_card_page = 1
            self._rate_line_page = 1
            self._set_selected_rate_card_id("")
            self._set_selected_rate_card(default_detail())
            self._set_rate_lines(default_collection())
            self.rateFiltersChanged.emit()
            self.refresh()

    def _set_rate_line_filters(
        self, search: str, rate_type: str, status: str, effective_status: str
    ) -> None:
        values = (
            str(search or "").strip(),
            str(rate_type or "").strip().lower(),
            str(status or "").strip().lower(),
            str(effective_status or "").strip().lower(),
        )
        current = (
            self._rate_line_search,
            self._rate_line_rate_type,
            self._rate_line_status,
            self._rate_line_effective_status,
        )
        if values != current:
            (
                self._rate_line_search,
                self._rate_line_rate_type,
                self._rate_line_status,
                self._rate_line_effective_status,
            ) = values
            self._rate_line_page = 1
            self.rateFiltersChanged.emit()
            self.refresh()

    def _set_budget_version_page(self, page: int) -> None:
        normalized_page = max(1, int(page))
        if normalized_page != self._budget_version_page:
            self._budget_version_page = normalized_page
            self.refresh()

    def _set_budget_version_sort(self, sort_key: str, sort_direction: int) -> None:
        key = str(sort_key or "").strip()
        if key != self._budget_version_sort_key or int(sort_direction) != self._budget_version_sort_direction:
            self._budget_version_sort_key = key
            self._budget_version_sort_direction = int(sort_direction)
            self._budget_version_page = 1
            self.budgetVersionSortKeyChanged.emit()
            self.budgetVersionSortDirectionChanged.emit()
            self.refresh()

    def _set_budget_line_sort(self, sort_key: str, sort_direction: int) -> None:
        key = str(sort_key or "").strip()
        if key != self._budget_line_sort_key or int(sort_direction) != self._budget_line_sort_direction:
            self._budget_line_sort_key = key
            self._budget_line_sort_direction = int(sort_direction)
            self._budget_line_page = 1
            self.budgetLineSortKeyChanged.emit()
            self.budgetLineSortDirectionChanged.emit()
            self.refresh()

    def _select_planned_cost_version(self, version_id: str) -> None:
        value = (version_id or "").strip()
        if value != self._selected_planned_cost_version_id:
            self._set_selected_planned_cost_version_id(value)
            self._planned_cost_line_page = 1
            self.refresh()

    def _set_planned_cost_version_page(self, page: int) -> None:
        normalized_page = max(1, int(page))
        if normalized_page != self._planned_cost_version_page:
            self._planned_cost_version_page = normalized_page
            self.refresh()

    def _set_planned_cost_version_sort(self, sort_key: str, sort_direction: int) -> None:
        key = str(sort_key or "").strip()
        if (
            key != self._planned_cost_version_sort_key
            or int(sort_direction) != self._planned_cost_version_sort_direction
        ):
            self._planned_cost_version_sort_key = key
            self._planned_cost_version_sort_direction = int(sort_direction)
            self._planned_cost_version_page = 1
            self.plannedCostVersionSortKeyChanged.emit()
            self.plannedCostVersionSortDirectionChanged.emit()
            self.refresh()

    def _set_planned_cost_line_sort(self, sort_key: str, sort_direction: int) -> None:
        key = str(sort_key or "").strip()
        if (
            key != self._planned_cost_line_sort_key
            or int(sort_direction) != self._planned_cost_line_sort_direction
        ):
            self._planned_cost_line_sort_key = key
            self._planned_cost_line_sort_direction = int(sort_direction)
            self._planned_cost_line_page = 1
            self.plannedCostLineSortKeyChanged.emit()
            self.plannedCostLineSortDirectionChanged.emit()
            self.refresh()

    def _select_financial_change(self, change_id: str) -> None:
        value = (change_id or "").strip()
        if value != self._selected_change_id:
            self._set_selected_change_id(value)
            self.refresh()

    def _select_variance_baseline(self, baseline_id: str) -> None:
        value = (baseline_id or "").strip()
        if value != self._selected_baseline_id:
            self._set_selected_baseline_id(value)
            self.refresh()

    def _set_configuration_page(self, collection: str, page: int) -> None:
        normalized_page = max(1, int(page))
        attribute = {
            "budget_lines": "_budget_line_page",
            "rate_lines": "_rate_line_page",
            "planned_cost_lines": "_planned_cost_line_page",
            "billing_preparations": "_billing_preparation_page",
        }.get(collection)
        if attribute is None or getattr(self, attribute) == normalized_page:
            return
        setattr(self, attribute, normalized_page)
        self.refresh()

    def _set_actual_page(self, page: int) -> None:
        normalized_page = max(1, int(page))
        if normalized_page != self._actual_page:
            self._actual_page = normalized_page
            self.refresh()

    def _set_commitment_page(self, page: int) -> None:
        normalized_page = max(1, int(page))
        if normalized_page != self._commitment_page:
            self._commitment_page = normalized_page
            self.refresh()

    def _set_transaction_page_size(self, page_size: int) -> None:
        normalized_size = max(1, min(int(page_size), 200))
        if normalized_size != self._transaction_page_size:
            self._transaction_page_size = normalized_size
            self._actual_page = 1
            self._commitment_page = 1
            self.refresh()

    def _set_actual_sort(self, sort_key: str, sort_direction: int) -> None:
        normalized_key = str(sort_key or "").strip()
        if (
            normalized_key != self._actual_sort_key
            or int(sort_direction) != self._actual_sort_direction
        ):
            self._actual_sort_key = normalized_key
            self._actual_sort_direction = int(sort_direction)
            self._actual_page = 1
            self.actualSortKeyChanged.emit()
            self.actualSortDirectionChanged.emit()
            self.refresh()

    def _set_commitment_sort(self, sort_key: str, sort_direction: int) -> None:
        normalized_key = str(sort_key or "").strip()
        if (
            normalized_key != self._commitment_sort_key
            or int(sort_direction) != self._commitment_sort_direction
        ):
            self._commitment_sort_key = normalized_key
            self._commitment_sort_direction = int(sort_direction)
            self._commitment_page = 1
            self.commitmentSortKeyChanged.emit()
            self.commitmentSortDirectionChanged.emit()
            self.refresh()

__all__ = ["FinancialsSelectionMixin"]
