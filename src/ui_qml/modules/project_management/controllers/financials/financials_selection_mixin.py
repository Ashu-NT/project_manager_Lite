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
        self.refresh()

    def _set_configuration_page(self, collection: str, page: int) -> None:
        normalized_page = max(1, int(page))
        attribute = {
            "budget_lines": "_budget_line_page",
            "rate_lines": "_rate_line_page",
            "planned_cost_lines": "_planned_cost_line_page",
        }.get(collection)
        if attribute is None or getattr(self, attribute) == normalized_page:
            return
        setattr(self, attribute, normalized_page)
        self.refresh()

__all__ = ["FinancialsSelectionMixin"]
