from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementDashboardDesktopApi,
    build_project_management_dashboard_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardOverviewViewModel,
)

from .overview_mapper import to_overview_view_model


class ProjectDashboardPresenter:
    def __init__(
        self,
        desktop_api: ProjectManagementDashboardDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_dashboard_desktop_api()

    def build_empty_overview(self) -> ProjectDashboardOverviewViewModel:
        return to_overview_view_model(self._desktop_api.build_empty_overview())

    def build_overview_from_dashboard_data(
        self, *, project_name: str, dashboard_data: Any
    ) -> ProjectDashboardOverviewViewModel:
        return to_overview_view_model(
            self._desktop_api.build_overview_from_dashboard_data(
                project_name=project_name,
                dashboard_data=dashboard_data,
            )
        )


__all__ = ["ProjectDashboardPresenter"]
