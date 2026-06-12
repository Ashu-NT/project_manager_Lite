from __future__ import annotations

from math import ceil

from src.ui_qml.modules.project_management.controllers.dashboard.dashboard_types import (
    DashboardMap,
    DashboardObjectList,
)


class DashboardOperationalTableMixin:
    def _set_operational_search_text_from_qml(self, search_text: str) -> None:
        normalized_text = (search_text or "").strip()
        if normalized_text == self._operational_search_text:
            return
        self._set_operational_search_text(normalized_text)
        self._set_operational_page(1)
        self._apply_operational_table_state()

    def _set_operational_page_from_qml(self, page: int) -> None:
        requested_page = max(1, int(page))
        if requested_page == self._operational_page:
            return
        self._set_operational_page(requested_page)
        self._apply_operational_table_state()

    def _set_operational_page_size_from_qml(self, page_size: int) -> None:
        requested_page_size = max(1, int(page_size))
        if requested_page_size == self._operational_page_size:
            return
        self._set_operational_page_size(requested_page_size)
        self._set_operational_page(1)
        self._apply_operational_table_state()

    def _select_operational_row_from_qml(self, row_id: str) -> None:
        self._set_selected_operational_row_id((row_id or "").strip())

    def _apply_operational_table_state(self) -> None:
        table = self._current_operational_table_source()
        all_rows = list(table.get("rows", []) or [])
        filtered_rows = self._filter_operational_rows(
            rows=all_rows,
            search_text=self._operational_search_text,
        )
        total_count = len(filtered_rows)
        self._set_operational_total_count(total_count)
        page_size = max(1, self._operational_page_size)
        total_pages = max(1, ceil(total_count / page_size)) if total_count else 1
        if self._operational_page > total_pages:
            self._set_operational_page(total_pages)
        page = max(1, self._operational_page)
        start_index = (page - 1) * page_size
        page_rows = filtered_rows[start_index : start_index + page_size]
        visible_row_ids = {str(row.get("id", "") or "") for row in page_rows}
        if (
            self._selected_operational_row_id
            and self._selected_operational_row_id not in visible_row_ids
        ):
            self._set_selected_operational_row_id("")
        self._set_operational_table(
            {
                "id": table.get("id", ""),
                "title": table.get("title", ""),
                "subtitle": table.get("subtitle", ""),
                "emptyState": table.get("emptyState", ""),
                "columns": list(table.get("columns", []) or []),
                "rows": page_rows,
            }
        )

    def _current_operational_table_source(self) -> DashboardMap:
        selected_id = self._selected_operational_tab_id
        for table in self._raw_operational_tables:
            if str(table.get("id", "") or "") == selected_id:
                return table
        if self._raw_operational_tables:
            return self._raw_operational_tables[0]
        return self._empty_operational_table()

    @staticmethod
    def _filter_operational_rows(
        *,
        rows: DashboardObjectList,
        search_text: str,
    ) -> DashboardObjectList:
        normalized = search_text.strip().lower()
        if not normalized:
            return rows
        filtered: DashboardObjectList = []
        for row in rows:
            haystacks = [
                str(value or "").lower()
                for key, value in row.items()
                if key not in {"state", "routeId"}
            ]
            if any(normalized in haystack for haystack in haystacks):
                filtered.append(row)
        return filtered

    @staticmethod
    def _default_operational_tab_id(
        selected_view_key: str,
        tables: DashboardObjectList,
    ) -> str:
        available_ids = [
            str(table.get("id", "") or "")
            for table in tables
            if str(table.get("id", "") or "")
        ]
        preferred_by_view = {
            "executive": "delayed_tasks",
            "pmo": "pending_approvals",
            "project_manager": "delayed_tasks",
            "resource_manager": "resource_overloads",
            "financial": "budget_variances",
        }
        preferred = preferred_by_view.get(selected_view_key, "")
        if preferred in available_ids:
            return preferred
        return available_ids[0] if available_ids else ""

    @staticmethod
    def _empty_operational_table() -> DashboardMap:
        return {
            "id": "",
            "title": "",
            "subtitle": "",
            "emptyState": "No dashboard rows are available yet.",
            "columns": [],
            "rows": [],
        }


__all__ = ["DashboardOperationalTableMixin"]
