from __future__ import annotations


class FinancialsSelectionMixin:
    def _select_project(self, project_id: str) -> None:
        normalized_value = (project_id or "").strip()
        if normalized_value == self._selected_project_id:
            return
        self._set_selected_project_id(normalized_value)
        self._set_selected_cost_id("")
        self.refresh()

    def _set_cost_type_filter(self, cost_type: str) -> None:
        normalized_value = (cost_type or "all").strip()
        if normalized_value == self._selected_cost_type:
            return
        self._set_selected_cost_type(normalized_value)
        self.refresh()

    def _set_search_text_from_qml(self, search_text: str) -> None:
        normalized_value = (search_text or "").strip()
        if normalized_value == self._search_text:
            return
        self._set_search_text(normalized_value)
        self.refresh()

    def _select_cost(self, cost_id: str) -> None:
        normalized_value = (cost_id or "").strip()
        if normalized_value == self._selected_cost_id:
            return
        self._set_selected_cost_id(normalized_value)
        self.refresh()


__all__ = ["FinancialsSelectionMixin"]
