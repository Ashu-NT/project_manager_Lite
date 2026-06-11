from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenancePlannerDesktopApi,
    build_maintenance_planner_desktop_api,
)
from src.ui_qml.modules.maintenance.view_models.planner import (
    MaintenancePlannerWorkspaceViewModel,
)

from .workspace_builder import build_workspace_state


class MaintenancePlannerWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: MaintenancePlannerDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_maintenance_planner_desktop_api()

    def build_workspace_state(
        self,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        request_queue: str = "",
        work_order_queue: str = "",
        search_text: str = "",
    ) -> MaintenancePlannerWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            site_id=site_id,
            asset_id=asset_id,
            system_id=system_id,
            request_queue=request_queue,
            work_order_queue=work_order_queue,
            search_text=search_text,
        )


__all__ = ["MaintenancePlannerWorkspacePresenter"]
