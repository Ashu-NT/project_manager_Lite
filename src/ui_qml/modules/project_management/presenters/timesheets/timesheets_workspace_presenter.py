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

from .command_handler import (
    add_time_entry,
    approve_period,
    delete_time_entry,
    lock_period,
    reject_period,
    submit_period,
    unlock_period,
    update_time_entry,
)
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
        project_id: str = "all",
        assignment_id: str | None = None,
        period_start: str = "",
        queue_status: str = "SUBMITTED",
        selected_entry_id: str | None = None,
        selected_queue_period_id: str | None = None,
    ) -> TimesheetsWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            project_id=project_id,
            assignment_id=assignment_id,
            period_start=period_start,
            queue_status=queue_status,
            selected_entry_id=selected_entry_id,
            selected_queue_period_id=selected_queue_period_id,
        )

    def build_review_period_detail(self, period_id: str) -> TimesheetDetailViewModel:
        return build_review_detail(self._desktop_api, period_id)

    def add_time_entry(self, payload: dict[str, Any]) -> None:
        add_time_entry(self._desktop_api, payload)

    def update_time_entry(self, payload: dict[str, Any]) -> None:
        update_time_entry(self._desktop_api, payload)

    def delete_time_entry(self, entry_id: str) -> None:
        delete_time_entry(self._desktop_api, entry_id)

    def submit_period(self, payload: dict[str, Any]) -> None:
        submit_period(self._desktop_api, payload)

    def approve_period(self, payload: dict[str, Any]) -> None:
        approve_period(self._desktop_api, payload)

    def reject_period(self, payload: dict[str, Any]) -> None:
        reject_period(self._desktop_api, payload)

    def lock_period(self, payload: dict[str, Any]) -> None:
        lock_period(self._desktop_api, payload)

    def unlock_period(self, payload: dict[str, Any]) -> None:
        unlock_period(self._desktop_api, payload)


__all__ = ["ProjectTimesheetsWorkspacePresenter"]
