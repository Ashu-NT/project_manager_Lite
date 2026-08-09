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

__all__ = ["FinancialsTableMixin"]
