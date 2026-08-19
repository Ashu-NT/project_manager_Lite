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
from src.core.platform.api.desktop.history.activity.activity import PlatformActivityDesktopApi
from src.core.platform.api.desktop.master_data.employee.employee import PlatformEmployeeDesktopApi
from src.core.platform.api.desktop.security.auth.user import PlatformUserDesktopApi
from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogWorkspaceViewModel,
)

from .assignment_command_handler import (
    accept_assignment,
    create_assignment,
    decline_assignment,
    delete_assignment,
    preview_assignment,
    update_assignment_allocation,
    update_assignment_planned_hours,
    validate_assignment,
)
from .assignments_builder import build_task_assignments_state
from .collaboration_builder import build_task_collaboration_state
from .collaboration_command_handler import (
    clear_task_collaboration_presence,
    delete_task_comment,
    edit_task_comment,
    mark_task_collaboration_read,
    post_task_comment,
    react_to_task_comment,
    remove_task_comment_reaction,
    touch_task_collaboration_presence,
)
from .dependency_command_handler import (
    create_dependency,
    delete_dependency,
    preview_create_dependency,
    preview_delete_dependency,
    preview_update_dependency,
    update_dependency,
)
from .dependencies_builder import build_task_dependencies_state
from .detail_builder import build_task_basic_detail_state, build_task_detail_state
from .schedule_impact_builder import build_schedule_impact_state
from .skill_requirements_builder import build_task_skill_requirements_state
from .task_activity_builder import build_task_activity_state
from .task_command_handler import (
    apply_bulk_status,
    bulk_delete_tasks,
    create_task,
    move_task_in_wbs,
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
    update_task_time_entry,
)
from .workspace_builder import build_workspace_state
from .task_mapper import to_task_record_view_model

class ProjectTasksWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementTasksDesktopApi | None = None,
        collaboration_desktop_api: ProjectManagementCollaborationDesktopApi | None = None,
        timesheets_desktop_api: ProjectManagementTimesheetsDesktopApi | None = None,
        user_api: PlatformUserDesktopApi | None = None,
        employee_api: PlatformEmployeeDesktopApi | None = None,
        activity_api: PlatformActivityDesktopApi | None = None,
        projects_desktop_api: object | None = None,
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
        self._user_api = user_api
        self._employee_api = employee_api
        self._activity_api = activity_api
        self._projects_desktop_api = projects_desktop_api

    def build_workspace_state(
        self,
        *,
        project_id: str | None = None,
        search_text: str = "",
        status_filter: str = "all",
        priority_filter: str = "all",
        schedule_filter: str = "all",
        selected_task_id: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "wbsCode",
        sort_direction: str = "asc",
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
            sort_key=sort_key,
            sort_direction=sort_direction,
        )

    def list_export_records(
        self,
        *,
        project_id: str | None = None,
        search_text: str = "",
        status_filter: str = "all",
        priority_filter: str = "all",
        schedule_filter: str = "all",
        sort_key: str = "wbsCode",
        sort_direction: str = "asc",
        batch_size: int = 500,
    ) -> tuple:
        records = []
        page = 1
        while True:
            result = self._desktop_api.list_task_page(
                project_id=project_id,
                search_text=search_text,
                status=status_filter,
                priority=priority_filter,
                schedule=schedule_filter,
                page=page,
                page_size=batch_size,
                sort_key=sort_key,
                sort_direction=sort_direction,
            )
            records.extend(to_task_record_view_model(item) for item in result.items)
            if page * result.page_size >= result.filtered_total:
                break
            page += 1
        return tuple(records)

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
        resource_filter: str = "",
        page: int = 1,
        page_size: int = 25,
        selected_time_entry_id: str | None = None,
    ) -> TaskCatalogWorkspaceViewModel:
        return build_task_time_state(
            self._desktop_api,
            self._timesheets_desktop_api,
            task_id=task_id,
            resource_filter=resource_filter,
            page=page,
            page_size=page_size,
            selected_time_entry_id=selected_time_entry_id,
        )

    def build_empty_task_time_state(self) -> TaskCatalogWorkspaceViewModel:
        return build_empty_task_time_state()

    def build_task_time_entries_refresh(
        self,
        *,
        task_id: str,
        resource_filter: str = "",
        page: int = 1,
        page_size: int = 25,
        selected_time_entry_id: str | None = None,
    ) -> TaskCatalogWorkspaceViewModel | None:
        return build_task_time_entries_refresh(
            self._desktop_api,
            task_id=task_id,
            resource_filter=resource_filter,
            page=page,
            page_size=page_size,
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

    def build_task_activity_state(
        self,
        *,
        task_id: str,
    ) -> TaskCatalogWorkspaceViewModel:
        return build_task_activity_state(
            self._activity_api,
            task_id=task_id,
            user_api=self._user_api,
            employee_api=self._employee_api,
        )

    def create_task(self, payload: dict[str, Any]) -> None:
        create_task(self._desktop_api, payload)

    def suggest_code(self, payload: dict[str, Any]) -> str:
        return suggest_code(self._desktop_api, payload)

    def update_task(self, payload: dict[str, Any]) -> None:
        update_task(self._desktop_api, payload)

    def move_task_in_wbs(self, payload: dict[str, Any]) -> None:
        move_task_in_wbs(self._desktop_api, payload)

    def update_progress(self, payload: dict[str, Any]) -> None:
        update_progress(self._desktop_api, payload)

    def create_assignment(self, payload: dict[str, Any]) -> None:
        create_assignment(self._desktop_api, payload)

    def update_assignment_allocation(self, payload: dict[str, Any]) -> None:
        update_assignment_allocation(self._desktop_api, payload)

    def update_assignment_planned_hours(self, payload: dict[str, Any]) -> None:
        update_assignment_planned_hours(self._desktop_api, payload)

    def get_project_resource_usage(self, project_resource_id: str) -> dict[str, object] | None:
        """Project Resource Context for the Assignment inspector (docs §44
        follow-up) -- reads the same ProjectResourceUsageFact the Projects ->
        Resources workspace already renders, via the Projects desktop API's
        existing get_project_resource_usage. No new calculation."""
        normalized_id = (project_resource_id or "").strip()
        if not normalized_id or self._projects_desktop_api is None:
            return None
        get_usage = getattr(self._projects_desktop_api, "get_project_resource_usage", None)
        if not callable(get_usage):
            return None
        try:
            usage = get_usage(normalized_id)
        except Exception:
            return None
        if usage is None:
            return None
        return {
            "projectResourceId": usage.project_resource_id,
            "projectId": usage.project_id,
            "resourceId": usage.resource_id,
            "plannedHoursLabel": usage.planned_hours_label,
            "allocatedToTasksHoursLabel": usage.allocated_to_tasks_hours_label,
            "unallocatedPlannedHoursLabel": usage.unallocated_planned_hours_label,
            "actualHoursLabel": usage.actual_hours_label,
            "remainingProjectHoursLabel": usage.remaining_project_hours_label,
            "plannedBurnPercent": usage.planned_burn_percent,
            "taskAssignmentCount": usage.task_assignment_count,
            "envelopeStatus": usage.envelope_status,
            "envelopeStatusLabel": usage.envelope_status_label,
            "burnStatus": usage.burn_status,
            "burnStatusLabel": usage.burn_status_label,
        }

    def add_task_time_entry(self, payload: dict[str, Any]) -> None:
        add_task_time_entry(self._timesheets_desktop_api, payload)

    def update_task_time_entry(self, payload: dict[str, Any]) -> None:
        update_task_time_entry(self._timesheets_desktop_api, payload)

    def delete_task_time_entry(self, entry_id: str) -> None:
        delete_task_time_entry(self._timesheets_desktop_api, entry_id)

    def delete_assignment(self, assignment_id: str) -> None:
        delete_assignment(self._desktop_api, assignment_id)

    def accept_assignment(self, assignment_id: str) -> None:
        accept_assignment(self._desktop_api, assignment_id)

    def decline_assignment(self, payload: dict[str, Any]) -> None:
        decline_assignment(self._desktop_api, payload)

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

    def preview_create_dependency(self, payload: dict[str, Any]) -> dict[str, object]:
        return preview_create_dependency(self._desktop_api, payload)

    def preview_update_dependency(self, payload: dict[str, Any]) -> dict[str, object]:
        return preview_update_dependency(self._desktop_api, payload)

    def preview_delete_dependency(self, dependency_id: str) -> dict[str, object]:
        return preview_delete_dependency(self._desktop_api, dependency_id)

    def post_task_comment(self, payload: dict[str, Any]) -> None:
        post_task_comment(self._collaboration_desktop_api, payload)

    def edit_task_comment(self, payload: dict[str, Any]) -> None:
        edit_task_comment(self._collaboration_desktop_api, payload)

    def delete_task_comment(self, payload: dict[str, Any]) -> None:
        delete_task_comment(self._collaboration_desktop_api, payload)

    def react_to_task_comment(self, payload: dict[str, Any]) -> None:
        react_to_task_comment(self._collaboration_desktop_api, payload)

    def remove_task_comment_reaction(self, payload: dict[str, Any]) -> None:
        remove_task_comment_reaction(self._collaboration_desktop_api, payload)

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
