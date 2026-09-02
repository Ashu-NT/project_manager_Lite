from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)


class FinancialsLookupMixin:
    def _search_finance_projects(
        self, search: str, page: int, page_size: int
    ) -> dict[str, object]:
        result = self._lookup_page(
            lambda: self._financials_workspace_presenter.search_finance_projects(
                search=search, page=page, page_size=page_size
            )
        )
        if result.get("ok"):
            selected = next(
                (
                    item
                    for item in self._project_options
                    if str(item.get("value", "")) == self._selected_project_id
                ),
                None,
            )
            items = list(result.get("items", []))
            if selected is not None and all(
                item.get("value") != selected.get("value") for item in items
            ):
                items.insert(0, selected)
            self._set_project_options(items)
        return result

    def _search_manual_actual_projects(
        self, search: str, page: int, page_size: int
    ) -> dict[str, object]:
        return self._lookup_page(
            lambda: self._financials_workspace_presenter.search_manual_actual_projects(
                search=search, page=page, page_size=page_size
            )
        )

    def _search_manual_actual_tasks(
        self, project_id: str, search: str, page: int, page_size: int
    ) -> dict[str, object]:
        return self._lookup_page(
            lambda: self._financials_workspace_presenter.search_manual_actual_tasks(
                project_id, search=search, page=page, page_size=page_size
            )
        )

    def _search_manual_actual_cost_codes(
        self,
        project_id: str,
        search: str,
        page: int,
        page_size: int,
        effective_on: str,
    ) -> dict[str, object]:
        return self._lookup_page(
            lambda: self._financials_workspace_presenter.search_manual_actual_cost_codes(
                project_id,
                search=search,
                page=page,
                page_size=page_size,
                effective_on=_optional_date(effective_on),
            )
        )

    def _resolve_manual_actual_project(self, project_id: str) -> dict[str, object]:
        return self._lookup_item(
            lambda: self._financials_workspace_presenter.resolve_manual_actual_project(
                project_id
            )
        )

    def _resolve_manual_actual_task(
        self, project_id: str, task_id: str
    ) -> dict[str, object]:
        return self._lookup_item(
            lambda: self._financials_workspace_presenter.resolve_manual_actual_task(
                project_id, task_id
            )
        )

    def _resolve_manual_actual_cost_code(
        self, project_id: str, cost_code_id: str, effective_on: str
    ) -> dict[str, object]:
        return self._lookup_item(
            lambda: self._financials_workspace_presenter.resolve_manual_actual_cost_code(
                project_id,
                cost_code_id,
                effective_on=_optional_date(effective_on),
            )
        )

    def _load_manual_actual_defaults(self, project_id: str) -> dict[str, object]:
        try:
            defaults = self._financials_workspace_presenter.get_manual_actual_defaults(
                project_id
            )
            return {
                "ok": True,
                "currencyCode": defaults.currency_code,
                "entryKinds": [
                    {"value": item.value, "label": item.label}
                    for item in defaults.entry_kinds
                ],
            }
        except Exception as exc:
            logger.exception("Manual Actual defaults lookup failed.")
            return _lookup_error(exc)

    def _search_budget_tasks(
        self, project_id: str, search: str, page: int, page_size: int
    ) -> dict[str, object]:
        return self._lookup_page(
            lambda: self._financials_workspace_presenter.search_budget_tasks(
                project_id, search=search, page=page, page_size=page_size
            )
        )

    def _resolve_budget_task(
        self, project_id: str, task_id: str
    ) -> dict[str, object]:
        return self._lookup_item(
            lambda: self._financials_workspace_presenter.resolve_budget_task(
                project_id, task_id
            )
        )

    def _search_budget_cost_codes(
        self, project_id: str, search: str, page: int, page_size: int
    ) -> dict[str, object]:
        return self._lookup_page(
            lambda: self._financials_workspace_presenter.search_budget_cost_codes(
                project_id, search=search, page=page, page_size=page_size
            )
        )

    def _resolve_budget_cost_code(
        self, project_id: str, cost_code_id: str
    ) -> dict[str, object]:
        return self._lookup_item(
            lambda: self._financials_workspace_presenter.resolve_budget_cost_code(
                project_id, cost_code_id
            )
        )

    def _search_forecast_tasks(
        self, project_id: str, search: str, page: int, page_size: int
    ) -> dict[str, object]:
        return self._lookup_page(
            lambda: self._financials_workspace_presenter.search_forecast_tasks(
                project_id, search=search, page=page, page_size=page_size
            )
        )

    def _search_forecast_cost_codes(
        self,
        project_id: str,
        search: str,
        page: int,
        page_size: int,
        effective_on: str,
    ) -> dict[str, object]:
        return self._lookup_page(
            lambda: self._financials_workspace_presenter.search_forecast_cost_codes(
                project_id,
                search=search,
                page=page,
                page_size=page_size,
                effective_on=_optional_date(effective_on),
            )
        )

    def _search_forecast_risks(
        self, project_id: str, search: str, page: int, page_size: int
    ) -> dict[str, object]:
        return self._lookup_page(
            lambda: self._financials_workspace_presenter.search_forecast_risks(
                project_id, search=search, page=page, page_size=page_size
            )
        )

    @staticmethod
    def _lookup_page(operation) -> dict[str, object]:
        try:
            page = operation()
            return {
                "ok": True,
                "items": [
                    {"value": item.value, "label": item.label}
                    for item in page.items
                ],
                "total": int(page.total),
                "page": int(page.page),
                "pageSize": int(page.page_size),
                "hasMore": bool(page.has_more),
            }
        except Exception as exc:
            logger.exception("Finance selector lookup failed.")
            return _lookup_error(exc)

    @staticmethod
    def _lookup_item(operation) -> dict[str, object]:
        try:
            item = operation()
            return {
                "ok": True,
                "item": (
                    {"value": item.value, "label": item.label}
                    if item is not None
                    else None
                ),
            }
        except Exception as exc:
            logger.exception("Finance selector item resolution failed.")
            return _lookup_error(exc)


def _optional_date(value: str) -> date | None:
    normalized = str(value or "").strip()
    return date.fromisoformat(normalized) if normalized else None


def _lookup_error(exc: Exception) -> dict[str, object]:
    return {
        "ok": False,
        "message": str(exc) or "The selector could not be loaded.",
        "code": str(getattr(exc, "code", "") or ""),
    }


__all__ = ["FinancialsLookupMixin"]
