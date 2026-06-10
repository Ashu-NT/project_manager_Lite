from __future__ import annotations

from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementCollaborationDesktopApi,
    ProjectManagementTasksDesktopApi,
    ProjectManagementTimesheetsDesktopApi,
    build_project_management_collaboration_desktop_api,
    build_project_management_tasks_desktop_api,
    build_project_management_timesheets_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogWorkspaceViewModel,
)

from .assignment_command_handler import (
    create_assignment,
    delete_assignment,
    preview_assignment,
    set_assignment_hours,
    update_assignment_allocation,
    validate_assignment,
)
from .assignments_builder import build_task_assignments_state
from .collaboration_builder import build_task_collaboration_state
from .collaboration_command_handler import (
    clear_task_collaboration_presence,
    mark_task_collaboration_read,
    post_task_comment,
    touch_task_collaboration_presence,
)
from .dependency_command_handler import (
    create_dependency,
    delete_dependency,
    update_dependency,
)
from .dependencies_builder import build_task_dependencies_state
from .detail_builder import build_task_basic_detail_state, build_task_detail_state
from .schedule_impact_builder import build_schedule_impact_state
from .skill_requirements_builder import build_task_skill_requirements_state
from .task_command_handler import (
    apply_bulk_status,
    bulk_delete_tasks,
    create_task,
    suggest_code,
    update_progress,
    update_task,
)
from .time_builder import (
    build_empty_task_time_state,
    build_task_time_entries_refresh,
    build_task_time_state,
)
from .time_command_handler import (
    add_task_time_entry,
    delete_task_time_entry,
    lock_task_period,
    submit_task_period,
    unlock_task_period,
    update_task_time_entry,
)
from .workspace_builder import build_workspace_state


class ProjectTasksWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementTasksDesktopApi | None = None,
        collaboration_desktop_api: ProjectManagementCollaborationDesktopApi | None = None,
        timesheets_desktop_api: ProjectManagementTimesheetsDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_tasks_desktop_api()
        self._collaboration_desktop_api = (
            collaboration_desktop_api
            or build_project_management_collaboration_desktop_api()
        )
        self._timesheets_desktop_api = (
            timesheets_desktop_api
            or build_project_management_timesheets_desktop_api()
        )

    def build_workspace_state(
        self,
        *,
        project_id: str | None = None,
        search_text: str = "",
        status_filter: str = "all",
        priority_filter: str = "all",
        schedule_filter: str = "all",
        selected_task_id: str | None = None,
        selected_assignment_id: str | None = None,
        selected_time_period_start: str = "",
        selected_time_entry_id: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> TaskCatalogWorkspaceViewModel:
        return build_workspace_state(
            self._desktop_api,
            project_id=project_id,
            search_text=search_text,
            status_filter=status_filter,
            priority_filter=priority_filter,
            schedule_filter=schedule_filter,
            selected_task_id=selected_task_id,
            page=page,
            page_size=page_size,
        )

    def build_task_basic_detail_state(
        self,
        *,
        task_id: str,
        project_id: str | None = None,
    ) -> TaskCatalogWorkspaceViewModel:
        return build_task_basic_detail_state(
            self._desktop_api,
            task_id=task_id,
            project_id=project_id,
        )

    def build_task_detail_state(
        self,
        *,
        task_id: str,
        project_id: str | None = None,
    ) -> TaskCatalogWorkspaceViewModel:
        return build_task_detail_state(
            self._desktop_api,
            task_id=task_id,
            project_id=project_id,
        )

    def build_task_assignments_state(
        self,
        *,
        task_id: str,
        project_id: str | None = None,
    ) -> TaskCatalogWorkspaceViewModel:
        return build_task_assignments_state(
            self._desktop_api,
            task_id=task_id,
            project_id=project_id,
        )

    def build_task_dependencies_state(
        self,
        *,
        task_id: str,
        project_id: str | None = None,
    ) -> TaskCatalogWorkspaceViewModel:
        return build_task_dependencies_state(
            self._desktop_api,
            task_id=task_id,
            project_id=project_id,
        )

    def build_task_time_state(
        self,
        *,
        task_id: str,
        selected_assignment_id: str | None = None,
        selected_time_period_start: str = "",
        selected_time_entry_id: str | None = None,
    ) -> TaskCatalogWorkspaceViewModel:
        return build_task_time_state(
            self._desktop_api,
            self._timesheets_desktop_api,
            task_id=task_id,
            selected_assignment_id=selected_assignment_id,
            selected_time_period_start=selected_time_period_start,
            selected_time_entry_id=selected_time_entry_id,
        )

    def build_empty_task_time_state(self) -> TaskCatalogWorkspaceViewModel:
        return build_empty_task_time_state()

    def build_task_time_entries_refresh(
        self,
        *,
        assignment_id: str | None,
        period_start: str = "",
        selected_time_entry_id: str | None = None,
    ) -> TaskCatalogWorkspaceViewModel | None:
        return build_task_time_entries_refresh(
            self._timesheets_desktop_api,
            assignment_id=assignment_id,
            period_start=period_start,
            selected_time_entry_id=selected_time_entry_id,
        )

    def build_task_collaboration_state(
        self,
        *,
        task_id: str,
    ) -> TaskCatalogWorkspaceViewModel:
        return build_task_collaboration_state(
            self._desktop_api,
            self._collaboration_desktop_api,
            task_id=task_id,
        )

    def build_task_schedule_impact_state(
        self,
        *,
        task_id: str,
        project_id: str | None = None,
    ) -> dict[str, object]:
        return build_schedule_impact_state(
            self._desktop_api,
            task_id=task_id,
            project_id=project_id,
        )

    def build_task_skill_requirements_state(
        self,
        *,
        task_id: str,
    ) -> TaskCatalogWorkspaceViewModel:
        return build_task_skill_requirements_state(
            self._desktop_api,
            task_id=task_id,
        )

    def create_task(self, payload: dict[str, Any]) -> None:
        create_task(self._desktop_api, payload)

    def suggest_code(self, payload: dict[str, Any]) -> str:
        return suggest_code(self._desktop_api, payload)

    def update_task(self, payload: dict[str, Any]) -> None:
        update_task(self._desktop_api, payload)

    def update_progress(self, payload: dict[str, Any]) -> None:
        update_progress(self._desktop_api, payload)

    def create_assignment(self, payload: dict[str, Any]) -> None:
        create_assignment(self._desktop_api, payload)

    def update_assignment_allocation(self, payload: dict[str, Any]) -> None:
        update_assignment_allocation(self._desktop_api, payload)

    def set_assignment_hours(self, payload: dict[str, Any]) -> None:
        set_assignment_hours(self._desktop_api, payload)

    def add_task_time_entry(self, payload: dict[str, Any]) -> None:
        add_task_time_entry(self._timesheets_desktop_api, payload)

    def update_task_time_entry(self, payload: dict[str, Any]) -> None:
        update_task_time_entry(self._timesheets_desktop_api, payload)

    def delete_task_time_entry(self, entry_id: str) -> None:
        delete_task_time_entry(self._timesheets_desktop_api, entry_id)

    def submit_task_period(self, payload: dict[str, Any]) -> None:
        submit_task_period(self._timesheets_desktop_api, payload)

    def lock_task_period(self, payload: dict[str, Any]) -> None:
        lock_task_period(self._timesheets_desktop_api, payload)

    def unlock_task_period(self, payload: dict[str, Any]) -> None:
        unlock_task_period(self._timesheets_desktop_api, payload)

    def delete_assignment(self, assignment_id: str) -> None:
        delete_assignment(self._desktop_api, assignment_id)

    def apply_bulk_status(self, payload: dict[str, Any]) -> None:
        apply_bulk_status(self._desktop_api, payload)

    def bulk_delete_tasks(self, task_ids: list[str] | tuple[str, ...]) -> None:
        bulk_delete_tasks(self._desktop_api, task_ids)

    def create_dependency(self, payload: dict[str, Any]) -> None:
        create_dependency(self._desktop_api, payload)

    def update_dependency(self, payload: dict[str, Any]) -> None:
        update_dependency(self._desktop_api, payload)

    def delete_dependency(self, dependency_id: str) -> None:
        delete_dependency(self._desktop_api, dependency_id)

    def post_task_comment(self, payload: dict[str, Any]) -> None:
        post_task_comment(self._collaboration_desktop_api, payload)

    def mark_task_collaboration_read(self, task_id: str) -> None:
        mark_task_collaboration_read(self._collaboration_desktop_api, task_id)

    def touch_task_collaboration_presence(
        self,
        task_id: str,
        *,
        activity: str = "reviewing",
    ) -> None:
        touch_task_collaboration_presence(
            self._collaboration_desktop_api,
            task_id,
            activity=activity,
        )

    def clear_task_collaboration_presence(self, task_id: str) -> None:
        clear_task_collaboration_presence(self._collaboration_desktop_api, task_id)

    def preview_assignment(self, payload: dict[str, Any]) -> dict[str, object]:
        return preview_assignment(self._desktop_api, payload)

    def validate_assignment(self, payload: dict[str, Any]) -> dict[str, object]:
        return validate_assignment(self._desktop_api, payload)


__all__ = ["ProjectTasksWorkspacePresenter"]
