from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementPortfolioDesktopApi,
    build_project_management_portfolio_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioWorkspaceViewModel,
)

from .command_handler import (
    activate_template,
    create_dependency,
    create_intake_item,
    create_scenario,
    create_template,
    remove_dependency,
    update_intake_item_status,
)
from .workspace_builder import build_workspace_state

class ProjectPortfolioWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementPortfolioDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_portfolio_desktop_api()

    def build_workspace_state(
        self,
        *,
        active_tab: str = "executive",
        intake_status_filter: str = "all",
        intake_search_text: str = "",
        intake_page: int = 1,
        intake_page_size: int = 25,
        intake_sort_key: str = "updatedAt",
        intake_sort_direction: str = "desc",
        heatmap_search_text: str = "",
        heatmap_status_filter: str | None = None,
        heatmap_page: int = 1,
        heatmap_page_size: int = 25,
        heatmap_sort_key: str = "projectName",
        heatmap_sort_direction: str = "asc",
        dependencies_search_text: str = "",
        dependencies_page: int = 1,
        dependencies_page_size: int = 25,
        dependencies_sort_key: str = "updatedAt",
        dependencies_sort_direction: str = "desc",
        selected_scenario_id: str | None = None,
        base_compare_scenario_id: str | None = None,
        compare_scenario_id: str | None = None,
    ) -> PortfolioWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            active_tab=active_tab,
            intake_status_filter=intake_status_filter,
            intake_search_text=intake_search_text,
            intake_page=intake_page,
            intake_page_size=intake_page_size,
            intake_sort_key=intake_sort_key,
            intake_sort_direction=intake_sort_direction,
            heatmap_search_text=heatmap_search_text,
            heatmap_status_filter=heatmap_status_filter,
            heatmap_page=heatmap_page,
            heatmap_page_size=heatmap_page_size,
            heatmap_sort_key=heatmap_sort_key,
            heatmap_sort_direction=heatmap_sort_direction,
            dependencies_search_text=dependencies_search_text,
            dependencies_page=dependencies_page,
            dependencies_page_size=dependencies_page_size,
            dependencies_sort_key=dependencies_sort_key,
            dependencies_sort_direction=dependencies_sort_direction,
            selected_scenario_id=selected_scenario_id,
            base_compare_scenario_id=base_compare_scenario_id,
            compare_scenario_id=compare_scenario_id,
        )

    def create_template(self, payload: dict[str, Any]) -> None:
        create_template(self._desktop_api, payload)

    def activate_template(self, template_id: str) -> None:
        activate_template(self._desktop_api, template_id)

    def create_intake_item(self, payload: dict[str, Any]) -> None:
        create_intake_item(self._desktop_api, payload)

    def create_scenario(self, payload: dict[str, Any]) -> None:
        create_scenario(self._desktop_api, payload)

    def create_dependency(self, payload: dict[str, Any]) -> None:
        create_dependency(self._desktop_api, payload)

    def remove_dependency(self, dependency_id: str) -> None:
        remove_dependency(self._desktop_api, dependency_id)

    def update_intake_item_status(self, item_id: str, status: str) -> None:
        update_intake_item_status(self._desktop_api, item_id, status)

__all__ = ["ProjectPortfolioWorkspacePresenter"]
