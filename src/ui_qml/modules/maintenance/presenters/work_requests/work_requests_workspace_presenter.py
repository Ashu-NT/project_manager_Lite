from __future__ import annotations

from src.core.modules.maintenance.api.desktop import (
    MaintenanceWorkRequestsDesktopApi,
    build_maintenance_work_requests_desktop_api,
)
from src.ui_qml.modules.maintenance.view_models.work_requests import (
    MaintenanceWorkRequestsWorkspaceViewModel,
)

from . import status_command_handler as _status
from . import work_request_command_handler as _wr
from .workspace_builder import build_workspace_state


class MaintenanceWorkRequestsWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: MaintenanceWorkRequestsDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_maintenance_work_requests_desktop_api()

    def build_workspace_state(
        self,
        *,
        search_text: str = "",
        site_filter: str = "all",
        status_filter: str = "all",
        priority_filter: str = "all",
        asset_filter: str = "all",
        selected_work_request_id: str | None = None,
    ) -> MaintenanceWorkRequestsWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            search_text=search_text,
            site_filter=site_filter,
            status_filter=status_filter,
            priority_filter=priority_filter,
            asset_filter=asset_filter,
            selected_work_request_id=selected_work_request_id,
        )

    def create_work_request(self, payload: dict) -> None:
        _wr.create_work_request(self._desktop_api, payload)

    def update_work_request(self, payload: dict) -> None:
        _wr.update_work_request(self._desktop_api, payload)

    def set_work_request_status(
        self,
        work_request_id: str,
        *,
        status: str,
        expected_version: int,
    ) -> None:
        _status.set_work_request_status(
            self._desktop_api,
            work_request_id,
            status=status,
            expected_version=expected_version,
        )


__all__ = ["MaintenanceWorkRequestsWorkspacePresenter"]
