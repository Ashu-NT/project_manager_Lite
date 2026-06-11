from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenanceWorkOrdersDesktopApi,
    build_maintenance_work_orders_desktop_api,
)
from src.ui_qml.modules.maintenance.view_models.work_orders import (
    MaintenanceWorkOrdersWorkspaceViewModel,
)

from . import status_command_handler as _status
from . import work_order_command_handler as _wo
from .workspace_builder import build_workspace_state


class MaintenanceWorkOrdersWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: MaintenanceWorkOrdersDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_maintenance_work_orders_desktop_api()

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        site_filter: str = "all",
        status_filter: str = "all",
        priority_filter: str = "all",
        work_order_type_filter: str = "all",
        asset_filter: str = "all",
        selected_work_order_id: str | None = None,
    ) -> MaintenanceWorkOrdersWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            search_text=search_text,
            site_filter=site_filter,
            status_filter=status_filter,
            priority_filter=priority_filter,
            work_order_type_filter=work_order_type_filter,
            asset_filter=asset_filter,
            selected_work_order_id=selected_work_order_id,
        )

    def create_work_order(self, payload: dict) -> None:
        _wo.create_work_order(self._desktop_api, payload)

    def update_work_order(self, payload: dict) -> None:
        _wo.update_work_order(self._desktop_api, payload)

    def set_work_order_status(
        self,
        work_order_id: str,
        *,
        status: str,
        expected_version: int,
    ) -> None:
        _status.set_work_order_status(
            self._desktop_api,
            work_order_id,
            status=status,
            expected_version=expected_version,
        )


__all__ = ["MaintenanceWorkOrdersWorkspacePresenter"]
