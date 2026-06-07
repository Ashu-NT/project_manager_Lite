from __future__ import annotations


class FinancialsTableMixin:
    def _set_cost_page_from_qml(self, page: int) -> None:
        requested_page = max(1, page)
        if requested_page == self._cost_page:
            return
        self._set_cost_page(requested_page)
        self.refresh()

    def _set_cost_page_size_from_qml(self, page_size: int) -> None:
        if page_size <= 0 or page_size == self._cost_page_size:
            return
        self._set_cost_page_size(page_size)
        self._set_cost_page(1)
        self.refresh()

    def _set_cost_bulk_selection(self, cost_id: str, selected: bool) -> None:
        ids = list(self._selected_cost_ids)
        if selected:
            if cost_id not in ids:
                ids.append(cost_id)
        else:
            ids = [item_id for item_id in ids if item_id != cost_id]
        self._set_selected_cost_ids(ids)

    def _select_visible_costs(self) -> None:
        ids = [
            str(item.get("id", ""))
            for item in (self._costs.get("items") or [])
            if item.get("id")
        ]
        self._set_selected_cost_ids(ids)

    def _clear_cost_bulk_selection(self) -> None:
        self._set_selected_cost_ids([])


__all__ = ["FinancialsTableMixin"]
