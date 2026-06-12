from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementSchedulingDesktopApi,
    build_project_management_scheduling_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingCollectionViewModel,
    SchedulingWorkspaceViewModel,
)

from .baseline_builder import build_baseline_variance_collection
from .command_handler import (
    approve_baseline,
    calculate_working_days,
    create_baseline,
    create_dependency,
    delete_baseline,
    delete_dependency,
    export_schedule,
    recalculate_schedule,
    reject_baseline,
    submit_baseline,
    update_dependency,
)
from .workspace_builder import build_workspace_state

class ProjectSchedulingWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementSchedulingDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_scheduling_desktop_api()

    def build_workspace_state(
        self,
        *,
        project_id: str | None = None,
        selected_calendar_id: str | None = None,
        selected_baseline_id: str | None = None,
        selected_baseline_a_id: str | None = None,
        selected_baseline_b_id: str | None = None,
        selected_status_filter: str = "all",
        search_text: str = "",
        show_critical_only: bool = False,
        show_delayed_only: bool = False,
        page: int = 1,
        page_size: int = 25,
        selected_activity_id: str | None = None,
        include_unchanged: bool = False,
        activity_log: tuple[dict[str, str], ...] = (),
    ) -> SchedulingWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            project_id=project_id,
            selected_calendar_id=selected_calendar_id,
            selected_baseline_id=selected_baseline_id,
            selected_baseline_a_id=selected_baseline_a_id,
            selected_baseline_b_id=selected_baseline_b_id,
            selected_status_filter=selected_status_filter,
            search_text=search_text,
            show_critical_only=show_critical_only,
            show_delayed_only=show_delayed_only,
            page=page,
            page_size=page_size,
            selected_activity_id=selected_activity_id,
            include_unchanged=include_unchanged,
            activity_log=activity_log,
        )

    def create_baseline(self, payload: dict[str, Any]) -> None:
        create_baseline(self._desktop_api, payload)

    def delete_baseline(self, baseline_id: str) -> None:
        delete_baseline(self._desktop_api, baseline_id)

    def submit_baseline(self, baseline_id: str) -> None:
        submit_baseline(self._desktop_api, baseline_id)

    def approve_baseline(self, baseline_id: str) -> None:
        approve_baseline(self._desktop_api, baseline_id)

    def reject_baseline(self, baseline_id: str) -> None:
        reject_baseline(self._desktop_api, baseline_id)

    def build_baseline_variance_collection(
        self,
        baseline_id: str,
    ) -> SchedulingCollectionViewModel:
        return build_baseline_variance_collection(self._desktop_api, baseline_id)

    def recalculate_schedule(self, project_id: str) -> None:
        recalculate_schedule(self._desktop_api, project_id)

    def create_dependency(self, payload: dict[str, Any]) -> None:
        create_dependency(self._desktop_api, payload)

    def update_dependency(self, payload: dict[str, Any]) -> None:
        update_dependency(self._desktop_api, payload)

    def delete_dependency(self, dependency_id: str) -> None:
        delete_dependency(self._desktop_api, dependency_id)

    def calculate_working_days(self, payload: dict[str, Any]) -> str:
        return calculate_working_days(self._desktop_api, payload)

    @staticmethod
    def export_schedule(project_id: str) -> str:
        return export_schedule(project_id)

__all__ = ["ProjectSchedulingWorkspacePresenter"]
