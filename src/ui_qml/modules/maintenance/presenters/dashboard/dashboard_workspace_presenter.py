from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenanceDashboardDesktopApi,
    build_maintenance_dashboard_desktop_api,
)
from src.ui_qml.modules.maintenance.view_models.dashboard import (
    MaintenanceDashboardWorkspaceViewModel,
)

from .workspace_builder import build_workspace_state


class MaintenanceDashboardWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: MaintenanceDashboardDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_maintenance_dashboard_desktop_api()

    def build_workspace_state(
        self,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        days: int = 90,
    ) -> MaintenanceDashboardWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            site_id=site_id,
            asset_id=asset_id,
            system_id=system_id,
            location_id=location_id,
            days=days,
        )


__all__ = ["MaintenanceDashboardWorkspacePresenter"]
