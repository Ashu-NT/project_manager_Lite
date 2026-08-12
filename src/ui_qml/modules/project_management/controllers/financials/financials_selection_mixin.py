from __future__ import annotations


class FinancialsSelectionMixin:
    def _select_project(self, project_id: str) -> None:
        normalized_value = (project_id or "").strip()
        if normalized_value == self._selected_project_id:
            return
        self._set_selected_project_id(normalized_value)
        self._budget_line_page = 1
        self._rate_line_page = 1
        self._planned_cost_line_page = 1
        self._billing_preparation_page = 1
        self._set_selected_forecast_id("")
        self._set_selected_change_id("")
        self._set_selected_baseline_id("")
        self.refresh()

    def _select_forecast_version(self, forecast_id: str) -> None:
        value = (forecast_id or "").strip()
        if value != self._selected_forecast_id:
            self._set_selected_forecast_id(value)
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

__all__ = ["FinancialsSelectionMixin"]
