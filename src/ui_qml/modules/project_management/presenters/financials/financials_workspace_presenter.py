from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementFinancialsDesktopApi,
    build_project_management_financials_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsForecastViewModel,
    FinancialsWorkspaceViewModel,
)

from .command_handler import create_cost_item, delete_cost_item, suggest_code, update_cost_item
from .workspace_builder import build_workspace_state, compute_forecast

class ProjectFinancialsWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementFinancialsDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_financials_desktop_api()

    def build_workspace_state(
        self,
        *,
        selected_project_id: str | None = None,
        selected_cost_type: str = "all",
        search_text: str = "",
        selected_cost_id: str | None = None,
    ) -> FinancialsWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            selected_project_id=selected_project_id,
            selected_cost_type=selected_cost_type,
            search_text=search_text,
            selected_cost_id=selected_cost_id,
        )

    def suggest_code(self, payload: dict[str, Any]) -> str:
        return suggest_code(self._desktop_api, payload)

    def create_cost_item(self, payload: dict[str, Any]) -> None:
        create_cost_item(self._desktop_api, payload)

    def update_cost_item(self, payload: dict[str, Any]) -> None:
        update_cost_item(self._desktop_api, payload)

    def delete_cost_item(self, cost_id: str) -> None:
        delete_cost_item(self._desktop_api, cost_id)

    def compute_forecast(
        self,
        selected_project_id: str | None,
        *,
        method: str = "bac_over_cpi",
    ) -> FinancialsForecastViewModel:
        return compute_forecast(self._desktop_api, selected_project_id, method=method)

__all__ = ["ProjectFinancialsWorkspacePresenter"]
