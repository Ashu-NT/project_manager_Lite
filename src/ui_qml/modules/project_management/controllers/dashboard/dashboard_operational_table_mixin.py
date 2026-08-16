from __future__ import annotations

from math import ceil

from src.ui_qml.modules.project_management.controllers.common import (
    serialize_dashboard_operational_table_view_models,
)
from src.ui_qml.modules.project_management.controllers.dashboard.dashboard_types import (
    DashboardMap,
    DashboardObjectList,
)

# Tab ids whose collection is genuinely SCALABLE (R3 -- Overview Scalable
# Queries) and therefore always server-paginated -- never sliced from a
# locally materialized list like the other, bounded operational tabs.
_SCALABLE_OPERATIONAL_TAB_IDS = frozenset({"delayed_tasks"})


class DashboardOperationalTableMixin:
    def _current_tab_supports(self, capability: str) -> bool:
        # SCALABLE tabs are always live-server-driven regardless of what the
        # (about-to-be-superseded) eager snapshot placeholder claims -- see
        # _apply_live_operational_table_state().
        if self._selected_operational_tab_id in _SCALABLE_OPERATIONAL_TAB_IDS:
            return True
        return bool(self._current_operational_table_source().get(capability, True))

    def _set_operational_search_text_from_qml(self, search_text: str) -> None:
        if not self._current_tab_supports("supportsSearch"):
            return
        normalized_text = (search_text or "").strip()
        if normalized_text == self._operational_search_text:
            return
        self._set_operational_search_text(normalized_text)
        self._set_operational_page(1)
        self._apply_current_operational_tab_state()

    def _set_operational_page_from_qml(self, page: int) -> None:
        if not self._current_tab_supports("supportsPagination"):
            return
        requested_page = max(1, int(page))
        if requested_page == self._operational_page:
            return
        self._set_operational_page(requested_page)
        self._apply_current_operational_tab_state()

    def _set_operational_page_size_from_qml(self, page_size: int) -> None:
        if not self._current_tab_supports("supportsPagination"):
            return
        requested_page_size = max(1, int(page_size))
        if requested_page_size == self._operational_page_size:
            return
        self._set_operational_page_size(requested_page_size)
        self._set_operational_page(1)
        self._apply_current_operational_tab_state()

    def _apply_current_operational_tab_state(self) -> None:
        """Route to a live, authoritative backend page for SCALABLE tabs;
        everything else keeps re-slicing the already-fetched, bounded
        snapshot (cheap and correct for genuinely small/complete/top_n
        collections -- see the R3 Overview Scalable Queries classification)."""
        if self._selected_operational_tab_id in _SCALABLE_OPERATIONAL_TAB_IDS:
            self._apply_live_operational_table_state()
        else:
            self._apply_operational_table_state()

    def _apply_live_operational_table_state(self) -> None:
        tab_id = self._selected_operational_tab_id
        if tab_id == "delayed_tasks":
            view_model = self._dashboard_workspace_presenter.list_delayed_tasks_page(
                project_id=self._selected_project_id or None,
                search_text=self._operational_search_text,
                page=self._operational_page,
                page_size=self._operational_page_size,
            )
        else:  # pragma: no cover - defensive, no other scalable tab exists yet
            return
        serialized = serialize_dashboard_operational_table_view_models([view_model])[0]
        if (
            self._selected_operational_row_id
            and self._selected_operational_row_id
            not in {str(row.get("id", "") or "") for row in serialized.get("rows", [])}
        ):
            self._set_selected_operational_row_id("")
        self._set_operational_total_count(int(serialized.get("totalCount", 0)))
        self._set_operational_page(int(serialized.get("page", 1)))
        self._set_operational_table(serialized)

    def _select_operational_row_from_qml(self, row_id: str) -> None:
        self._set_selected_operational_row_id((row_id or "").strip())

    def _apply_operational_table_state(self) -> None:
        table = self._current_operational_table_source()
        all_rows = list(table.get("rows", []) or [])
        supports_search = bool(table.get("supportsSearch", True))
        supports_pagination = bool(table.get("supportsPagination", True))
        filtered_rows = self._filter_operational_rows(
            rows=all_rows,
            search_text=self._operational_search_text if supports_search else "",
        )
        total_count = len(filtered_rows)
        self._set_operational_total_count(total_count)
        if supports_pagination:
            page_size = max(1, self._operational_page_size)
            total_pages = max(1, ceil(total_count / page_size)) if total_count else 1
            if self._operational_page > total_pages:
                self._set_operational_page(total_pages)
            page = max(1, self._operational_page)
            start_index = (page - 1) * page_size
            page_rows = filtered_rows[start_index : start_index + page_size]
        else:
            self._set_operational_page(1)
            page_rows = filtered_rows
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
                "collectionSemantics": table.get("collectionSemantics", "complete"),
                "supportsSearch": supports_search,
                "supportsPagination": supports_pagination,
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

    # Categories surfaced in the "Attention Required" panel and how to turn
    # each table's own row shape into a normalized {title, subtitle,
    # statusLabel} triple. All three source tables are already bounded/
    # top_n/recent with real, truthful data (see the R3 Overview Scalable
    # Queries classification) -- no new query, just a compact digest of
    # data the Operational Views tabs already show in full.
    _ATTENTION_CATEGORIES = (
        ("delayed_tasks", "Delayed", "taskName", "owner"),
        ("high_risks", "Risk", "title", "owner"),
        ("pending_approvals", "Approval", "request", "requestedBy"),
    )
    _ATTENTION_ITEMS_PER_CATEGORY = 2

    def _build_attention_items(self) -> DashboardObjectList:
        tables_by_id = {
            str(table.get("id", "") or ""): table for table in self._raw_operational_tables
        }
        items: DashboardObjectList = []
        for table_id, category_label, title_key, subtitle_key in self._ATTENTION_CATEGORIES:
            table = tables_by_id.get(table_id)
            if table is None:
                continue
            for row in list(table.get("rows", []) or [])[: self._ATTENTION_ITEMS_PER_CATEGORY]:
                items.append(
                    {
                        "id": str(row.get("id", "") or ""),
                        "category": category_label,
                        "title": str(row.get(title_key, "") or ""),
                        "subtitle": str(row.get(subtitle_key, "") or ""),
                        "statusLabel": str(row.get("statusLabel", "") or category_label),
                        "routeId": str(row.get("routeId", "") or ""),
                        "state": dict(row.get("state", {}) or {}),
                    }
                )
        return items

    @staticmethod
    def _empty_operational_table() -> DashboardMap:
        return {
            "id": "",
            "title": "",
            "subtitle": "",
            "emptyState": "No dashboard rows are available yet.",
            "collectionSemantics": "complete",
            "supportsSearch": False,
            "supportsPagination": False,
            "columns": [],
            "rows": [],
        }


__all__ = ["DashboardOperationalTableMixin"]
