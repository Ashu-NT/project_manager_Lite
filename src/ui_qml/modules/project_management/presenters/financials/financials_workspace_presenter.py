from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementFinancialsDesktopApi,
    build_project_management_financials_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.financials import FinancialsWorkspaceViewModel

from .command_handler import create_manual_actual
from .workspace_builder import build_workspace_state

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
        budget_line_page: int = 1,
        rate_line_page: int = 1,
        planned_cost_line_page: int = 1,
        configuration_page_size: int = 50,
    ) -> FinancialsWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            selected_project_id=selected_project_id,
            budget_line_page=budget_line_page,
            rate_line_page=rate_line_page,
            planned_cost_line_page=planned_cost_line_page,
            configuration_page_size=configuration_page_size,
        )

    def create_manual_actual(self, payload: dict[str, Any]) -> None:
        create_manual_actual(self._desktop_api, payload)

__all__ = ["ProjectFinancialsWorkspacePresenter"]
