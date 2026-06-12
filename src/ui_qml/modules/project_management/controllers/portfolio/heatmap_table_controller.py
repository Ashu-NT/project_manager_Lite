from __future__ import annotations

from typing import Callable

from src.ui_qml.shared.models.data_table_model import DynamicTableModel

class HeatmapTableController:
    def __init__(self) -> None:
        self.search_text = ""
        self.page = 1
        self.page_size = 25
        self.total_count = 0
        self.visible_row_ids: list[str] = []

    def rebuild(
        self,
        heatmap_items: list[dict],
        table_model: DynamicTableModel,
        emit_page_changed: Callable,
        emit_total_count_changed: Callable,
        emit_visible_ids_changed: Callable,
    ) -> None:
        items = list(heatmap_items)
        search = self.search_text.casefold()
        if search:
            items = [
                item for item in items
                if search in str(item.get("title", "")).casefold()
            ]

        total_count = len(items)
        max_page = max(1, (total_count + self.page_size - 1) // self.page_size)
        if self.page > max_page:
            self.page = max_page
            emit_page_changed()

        start = (self.page - 1) * self.page_size
        page_rows = items[start: start + self.page_size]
        table_model.set_rows(page_rows)

        if total_count != self.total_count:
            self.total_count = total_count
            emit_total_count_changed()

        visible_row_ids = [
            str(item.get("id", "") or "")
            for item in page_rows
            if str(item.get("id", "") or "")
        ]
        if visible_row_ids != self.visible_row_ids:
            self.visible_row_ids = visible_row_ids
            emit_visible_ids_changed()

__all__ = ["HeatmapTableController"]
