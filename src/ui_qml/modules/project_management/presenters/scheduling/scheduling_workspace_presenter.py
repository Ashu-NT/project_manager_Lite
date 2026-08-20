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
    apply_resource_leveling,
    approve_baseline,
    calculate_working_days,
    create_baseline,
    create_dependency,
    delete_baseline,
    delete_dependency,
    recalculate_schedule,
    reject_baseline,
    submit_baseline,
    update_dependency,
)
from .leveling_builder import build_resource_leveling_state
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
        sort_key: str = "schedule",
        sort_direction: str = "asc",
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
            sort_key=sort_key,
            sort_direction=sort_direction,
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

    def preview_resource_leveling(self, project_id: str) -> dict[str, object]:
        return build_resource_leveling_state(self._desktop_api, project_id)

    def apply_resource_leveling(self, project_id: str) -> None:
        apply_resource_leveling(self._desktop_api, project_id)

    def create_dependency(self, payload: dict[str, Any]) -> None:
        create_dependency(self._desktop_api, payload)

    def update_dependency(self, payload: dict[str, Any]) -> None:
        update_dependency(self._desktop_api, payload)

    def delete_dependency(self, dependency_id: str) -> None:
        delete_dependency(self._desktop_api, dependency_id)

    def calculate_working_days(self, payload: dict[str, Any]) -> str:
        return calculate_working_days(self._desktop_api, payload)

__all__ = ["ProjectSchedulingWorkspacePresenter"]
