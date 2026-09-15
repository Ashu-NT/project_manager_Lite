from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementTimesheetsDesktopApi,
    build_project_management_timesheets_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetDetailViewModel,
    TimesheetsWorkspaceViewModel,
)

from .command_handler import approve_period, lock_period, reject_period, unlock_period
from .review_builder import build_review_detail
from .workspace_builder import build_workspace_state

class ProjectTimesheetsWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementTimesheetsDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_timesheets_desktop_api()

    def build_workspace_state(
        self,
        *,
        queue_status: str = "SUBMITTED",
        queue_search_text: str = "",
        queue_project_id: str = "all",
        queue_resource_id: str = "all",
        queue_period_start_from: str = "",
        queue_period_start_to: str = "",
        queue_sort_key: str = "submittedAt",
        queue_sort_direction: str = "desc",
        selected_queue_period_id: str | None = None,
        queue_page: int = 1,
        queue_page_size: int = 25,
    ) -> TimesheetsWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            queue_status=queue_status,
            queue_search_text=queue_search_text,
            queue_project_id=queue_project_id,
            queue_resource_id=queue_resource_id,
            queue_period_start_from=queue_period_start_from,
            queue_period_start_to=queue_period_start_to,
            queue_sort_key=queue_sort_key,
            queue_sort_direction=queue_sort_direction,
            selected_queue_period_id=selected_queue_period_id,
            queue_page=queue_page,
            queue_page_size=queue_page_size,
        )

    def build_review_period_detail(self, period_id: str) -> TimesheetDetailViewModel:
        return build_review_detail(self._desktop_api, period_id)

    def approve_period(self, payload: dict[str, Any]) -> None:
        approve_period(self._desktop_api, payload)

    def reject_period(self, payload: dict[str, Any]) -> None:
        reject_period(self._desktop_api, payload)

    def lock_period(self, payload: dict[str, Any]) -> None:
        lock_period(self._desktop_api, payload)

    def unlock_period(self, payload: dict[str, Any]) -> None:
        unlock_period(self._desktop_api, payload)

__all__ = ["ProjectTimesheetsWorkspacePresenter"]
