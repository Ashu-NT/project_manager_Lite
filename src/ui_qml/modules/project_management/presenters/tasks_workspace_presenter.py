from __future__ import annotations

from datetime import date
from typing import Any

from src.core.modules.project_management.api.desktop import (
    ProjectManagementTasksDesktopApi,
    TaskAssignmentAllocationCommand,
    TaskAssignmentCreateCommand,
    TaskAssignmentHoursCommand,
    TaskCreateCommand,
    TaskDependencyCreateCommand,
    TaskProgressCommand,
    TaskUpdateCommand,
    build_project_management_tasks_desktop_api,
)
from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogMetricViewModel,
    TaskCatalogOverviewViewModel,
    TaskCatalogWorkspaceViewModel,
    TaskDetailFieldViewModel,
    TaskDetailViewModel,
    TaskExecutionCollectionViewModel,
    TaskRecordViewModel,
    TaskSelectorOptionViewModel,
)


class ProjectTasksWorkspacePresenter:
    def __init__(
        self,
        *,
        desktop_api: ProjectManagementTasksDesktopApi | None = None,
    ) -> None:
        self._desktop_api = desktop_api or build_project_management_tasks_desktop_api()

    def build_workspace_state(
        self,
        *,
        project_id: str | None = None,
        search_text: str = "",
        status_filter: str = "all",
        selected_task_id: str | None = None,
    ) -> TaskCatalogWorkspaceViewModel:
        project_options = tuple(
            TaskSelectorOptionViewModel(value=option.value, label=option.label)
            for option in self._desktop_api.list_projects()
        )
        resolved_project_id = self._resolve_project_id(project_id, project_options)
        status_options = (
            TaskSelectorOptionViewModel(value="all", label="All statuses"),
            *(
                TaskSelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_statuses()
            ),
        )
        normalized_search = (search_text or "").strip()
        normalized_status_filter = self._normalize_status_filter(
            status_filter,
            status_options,
        )
        all_tasks = (
            self._desktop_api.list_tasks(resolved_project_id)
            if resolved_project_id
            else ()
        )
        filtered_tasks = tuple(
            task
            for task in all_tasks
            if self._matches_status(task, normalized_status_filter)
            and self._matches_search(task, normalized_search)
        )
        resolved_task_id = self._resolve_task_id(selected_task_id, filtered_tasks)
        selected_task = next(
            (task for task in filtered_tasks if task.id == resolved_task_id),
            None,
        )
        assignment_options = tuple(
            TaskSelectorOptionViewModel(value=option.value, label=option.label)
            for option in self._desktop_api.list_project_resources(resolved_project_id)
        )
        dependency_type_options = tuple(
            TaskSelectorOptionViewModel(value=option.value, label=option.label)
            for option in self._desktop_api.list_dependency_types()
        )
        dependency_task_options = tuple(
            TaskSelectorOptionViewModel(value=task.id, label=task.name)
            for task in all_tasks
            if task.id != resolved_task_id
        )
        assignments = (
            self._desktop_api.list_assignments(resolved_task_id)
            if resolved_task_id
            else ()
        )
        dependencies = (
            self._desktop_api.list_dependencies(resolved_task_id)
            if resolved_task_id
            else ()
        )

        return TaskCatalogWorkspaceViewModel(
            overview=self._build_overview(
                all_tasks=all_tasks,
                filtered_tasks=filtered_tasks,
            ),
            project_options=project_options,
            selected_project_id=resolved_project_id,
            status_options=status_options,
            selected_status_filter=normalized_status_filter,
            search_text=normalized_search,
            tasks=tuple(
                self._to_task_record_view_model(task)
                for task in filtered_tasks
            ),
            selected_task_id=resolved_task_id,
            selected_task_detail=self._build_detail_view_model(
                selected_task,
                assignment_count=len(assignments),
                dependency_count=len(dependencies),
            ),
            assignment_options=assignment_options,
            dependency_task_options=dependency_task_options,
            dependency_type_options=dependency_type_options,
            assignments=self._build_assignments_collection(
                selected_task=selected_task,
                assignments=assignments,
                assignment_options=assignment_options,
            ),
            dependencies=self._build_dependencies_collection(
                selected_task=selected_task,
                all_tasks=all_tasks,
                dependencies=dependencies,
            ),
            empty_state=self._build_empty_state(
                project_options=project_options,
                all_tasks=all_tasks,
                filtered_tasks=filtered_tasks,
                search_text=normalized_search,
                status_filter=normalized_status_filter,
            ),
        )

    def create_task(self, payload: dict[str, Any]) -> None:
        command = TaskCreateCommand(
            project_id=self._require_text(
                payload,
                "projectId",
                "Select a project before creating a task.",
            ),
            name=self._require_text(payload, "name", "Task name is required."),
            description=self._optional_text(payload, "description") or "",
            start_date=self._optional_date(payload, "startDate"),
            duration_days=self._optional_int(payload, "durationDays"),
            status=self._optional_text(payload, "status") or "TODO",
            priority=self._optional_int(payload, "priority"),
            deadline=self._optional_date(payload, "deadline"),
        )
        self._desktop_api.create_task(command)

    def update_task(self, payload: dict[str, Any]) -> None:
        command = TaskUpdateCommand(
            task_id=self._require_text(
                payload,
                "taskId",
                "Task ID is required for updates.",
            ),
            name=self._require_text(payload, "name", "Task name is required."),
            description=self._optional_text(payload, "description") or "",
            start_date=self._optional_date(payload, "startDate"),
            duration_days=self._optional_int(payload, "durationDays"),
            status=self._optional_text(payload, "status") or "TODO",
            priority=self._optional_int(payload, "priority"),
            deadline=self._optional_date(payload, "deadline"),
            expected_version=self._optional_int(payload, "expectedVersion"),
        )
        self._desktop_api.update_task(command)

    def update_progress(self, payload: dict[str, Any]) -> None:
        command = TaskProgressCommand(
            task_id=self._require_text(
                payload,
                "taskId",
                "Task ID is required for progress updates.",
            ),
            percent_complete=self._optional_float(payload, "percentComplete"),
            actual_start=self._optional_date(payload, "actualStart"),
            actual_end=self._optional_date(payload, "actualEnd"),
            status=self._optional_text(payload, "status"),
            expected_version=self._optional_int(payload, "expectedVersion"),
        )
        self._desktop_api.update_progress(command)

    def create_assignment(self, payload: dict[str, Any]) -> None:
        command = TaskAssignmentCreateCommand(
            task_id=self._require_text(
                payload,
                "taskId",
                "Select a task before assigning resources.",
            ),
            project_resource_id=self._require_text(
                payload,
                "projectResourceId",
                "Select a project resource to assign.",
            ),
            allocation_percent=self._require_float(
                payload,
                "allocationPercent",
                "Allocation percent is required.",
            ),
        )
        self._desktop_api.create_assignment(command)

    def update_assignment_allocation(self, payload: dict[str, Any]) -> None:
        command = TaskAssignmentAllocationCommand(
            assignment_id=self._require_text(
                payload,
                "assignmentId",
                "Assignment ID is required for allocation updates.",
            ),
            allocation_percent=self._require_float(
                payload,
                "allocationPercent",
                "Allocation percent is required.",
            ),
        )
        self._desktop_api.update_assignment_allocation(command)

    def set_assignment_hours(self, payload: dict[str, Any]) -> None:
        command = TaskAssignmentHoursCommand(
            assignment_id=self._require_text(
                payload,
                "assignmentId",
                "Assignment ID is required for effort updates.",
            ),
            hours_logged=self._require_float(
                payload,
                "hoursLogged",
                "Hours logged is required.",
            ),
        )
        self._desktop_api.set_assignment_hours(command)

    def delete_assignment(self, assignment_id: str) -> None:
        normalized_assignment_id = (assignment_id or "").strip()
        if not normalized_assignment_id:
            raise ValueError("Assignment ID is required to remove an assignment.")
        self._desktop_api.delete_assignment(normalized_assignment_id)

    def create_dependency(self, payload: dict[str, Any]) -> None:
        command = TaskDependencyCreateCommand(
            task_id=self._require_text(
                payload,
                "taskId",
                "Select a task before creating a dependency.",
            ),
            linked_task_id=self._require_text(
                payload,
                "linkedTaskId",
                "Select the linked task for this dependency.",
            ),
            relationship_direction=self._require_text(
                payload,
                "relationshipDirection",
                "Select the dependency relationship direction.",
            ),
            dependency_type=self._optional_text(payload, "dependencyType") or "FS",
            lag_days=self._optional_int(payload, "lagDays") or 0,
        )
        self._desktop_api.create_dependency(command)

    def delete_dependency(self, dependency_id: str) -> None:
        normalized_dependency_id = (dependency_id or "").strip()
        if not normalized_dependency_id:
            raise ValueError("Dependency ID is required to remove a dependency.")
        self._desktop_api.delete_dependency(normalized_dependency_id)

    @staticmethod
    def _build_overview(*, all_tasks, filtered_tasks) -> TaskCatalogOverviewViewModel:
        today = date.today()

        def count_by_status(status: str) -> int:
            return sum(1 for task in all_tasks if task.status == status)

        overdue_count = sum(
            1
            for task in all_tasks
            if task.deadline is not None
            and task.deadline < today
            and task.status != "DONE"
        )
        return TaskCatalogOverviewViewModel(
            title="Tasks",
            subtitle=(
                "Task planning, progress, dependencies, assignments, and "
                "execution state."
            ),
            metrics=(
                TaskCatalogMetricViewModel(
                    label="Total tasks",
                    value=str(len(all_tasks)),
                    supporting_text=(
                        f"Showing {len(filtered_tasks)} with the current filters."
                    ),
                ),
                TaskCatalogMetricViewModel(
                    label="In progress",
                    value=str(count_by_status("IN_PROGRESS")),
                    supporting_text="Active execution tasks.",
                ),
                TaskCatalogMetricViewModel(
                    label="Blocked",
                    value=str(count_by_status("BLOCKED")),
                    supporting_text="Needs intervention.",
                ),
                TaskCatalogMetricViewModel(
                    label="Done",
                    value=str(count_by_status("DONE")),
                    supporting_text="Completed scope.",
                ),
                TaskCatalogMetricViewModel(
                    label="Overdue",
                    value=str(overdue_count),
                    supporting_text="Past deadline and not done.",
                ),
            ),
        )

    def _build_detail_view_model(
        self,
        task,
        *,
        assignment_count: int,
        dependency_count: int,
    ) -> TaskDetailViewModel:
        if task is None:
            return TaskDetailViewModel(
                title="No task selected",
                empty_state=(
                    "Select a task from the catalog to review details or "
                    "update progress."
                ),
            )
        state = self._build_task_state(task)
        return TaskDetailViewModel(
            id=task.id,
            title=task.name,
            status_label=task.status_label,
            subtitle=task.project_name or "Project task",
            description=task.description or "No task description has been added yet.",
            fields=(
                TaskDetailFieldViewModel(
                    label="Start",
                    value=state["startDateLabel"],
                ),
                TaskDetailFieldViewModel(
                    label="Finish",
                    value=state["endDateLabel"],
                ),
                TaskDetailFieldViewModel(
                    label="Duration",
                    value=state["durationLabel"],
                ),
                TaskDetailFieldViewModel(
                    label="Deadline",
                    value=state["deadlineLabel"],
                ),
                TaskDetailFieldViewModel(
                    label="Progress",
                    value=state["percentCompleteLabel"],
                    supporting_text=f"Priority: {state['priorityLabel']}",
                ),
                TaskDetailFieldViewModel(
                    label="Actuals",
                    value=state["actualStartLabel"],
                    supporting_text=f"Actual end: {state['actualEndLabel']}",
                ),
                TaskDetailFieldViewModel(
                    label="Assignments",
                    value=str(assignment_count),
                    supporting_text="Resource allocations linked to this task.",
                ),
                TaskDetailFieldViewModel(
                    label="Dependencies",
                    value=str(dependency_count),
                    supporting_text="Predecessor and successor links in the plan.",
                ),
                TaskDetailFieldViewModel(
                    label="Version",
                    value=str(state["version"]),
                ),
            ),
            state=state,
        )

    def _build_assignments_collection(
        self,
        *,
        selected_task,
        assignments,
        assignment_options: tuple[TaskSelectorOptionViewModel, ...],
    ) -> TaskExecutionCollectionViewModel:
        if selected_task is None:
            return TaskExecutionCollectionViewModel(
                title="Assignments",
                subtitle="Resource coverage and effort capture for the selected task.",
                empty_state=(
                    "Select a task to review assignments and effort coverage."
                ),
            )
        if assignments:
            return TaskExecutionCollectionViewModel(
                title="Assignments",
                subtitle="Resource allocations and logged effort for this task.",
                items=tuple(
                    self._to_assignment_record_view_model(assignment)
                    for assignment in assignments
                ),
            )
        if not assignment_options:
            empty_state = (
                "No active project resources are available for the selected "
                "task's project."
            )
        else:
            empty_state = "No assignments are linked to the selected task yet."
        return TaskExecutionCollectionViewModel(
            title="Assignments",
            subtitle="Resource allocations and logged effort for this task.",
            empty_state=empty_state,
        )

    def _build_dependencies_collection(
        self,
        *,
        selected_task,
        all_tasks,
        dependencies,
    ) -> TaskExecutionCollectionViewModel:
        if selected_task is None:
            return TaskExecutionCollectionViewModel(
                title="Dependencies",
                subtitle="Predecessor and successor links for the selected task.",
                empty_state=(
                    "Select a task to review predecessor and successor links."
                ),
            )
        if dependencies:
            return TaskExecutionCollectionViewModel(
                title="Dependencies",
                subtitle="Sequencing links and lag settings for this task.",
                items=tuple(
                    self._to_dependency_record_view_model(dependency)
                    for dependency in dependencies
                ),
            )
        if len(all_tasks) <= 1:
            empty_state = "At least two project tasks are required to create a dependency."
        else:
            empty_state = "No dependencies are linked to the selected task yet."
        return TaskExecutionCollectionViewModel(
            title="Dependencies",
            subtitle="Sequencing links and lag settings for this task.",
            empty_state=empty_state,
        )

    def _to_task_record_view_model(self, task) -> TaskRecordViewModel:
        state = self._build_task_state(task)
        return TaskRecordViewModel(
            id=task.id,
            title=task.name,
            status_label=task.status_label,
            subtitle=(
                f"{state['projectName']} | Start {state['startDateLabel']} | "
                f"Finish {state['endDateLabel']}"
            ),
            supporting_text=(
                f"Progress: {state['percentCompleteLabel']} | "
                f"Deadline: {state['deadlineLabel']} | "
                f"Priority: {state['priorityLabel']}"
            ),
            meta_text=task.description or "No task description has been added yet.",
            state=state,
        )

    @staticmethod
    def _to_assignment_record_view_model(assignment) -> TaskRecordViewModel:
        allocation_percent = float(assignment.allocation_percent or 0.0)
        hours_logged = float(assignment.hours_logged or 0.0)
        state = {
            "assignmentId": assignment.id,
            "taskId": assignment.task_id,
            "resourceId": assignment.resource_id,
            "resourceName": assignment.resource_name,
            "allocationPercent": f"{allocation_percent:.1f}",
            "hoursLogged": f"{hours_logged:.2f}",
            "projectResourceId": assignment.project_resource_id or "",
        }
        return TaskRecordViewModel(
            id=assignment.id,
            title=assignment.resource_name,
            status_label=f"{allocation_percent:.1f}%",
            subtitle="Current allocation commitment",
            supporting_text=f"Hours logged: {hours_logged:.2f}",
            meta_text=f"Resource ID: {assignment.resource_id}",
            state=state,
        )

    @staticmethod
    def _to_dependency_record_view_model(dependency) -> TaskRecordViewModel:
        lag_label = f"{int(dependency.lag_days):+d}d"
        state = {
            "dependencyId": dependency.id,
            "linkedTaskId": dependency.linked_task_id,
            "linkedTaskName": dependency.linked_task_name,
            "direction": dependency.direction,
            "directionLabel": dependency.direction_label,
            "dependencyType": dependency.dependency_type,
            "dependencyTypeLabel": dependency.dependency_type_label,
            "lagDays": str(int(dependency.lag_days)),
            "relationshipLabel": dependency.relationship_label,
        }
        return TaskRecordViewModel(
            id=dependency.id,
            title=dependency.linked_task_name,
            status_label=dependency.direction_label,
            subtitle=(
                f"{dependency.dependency_type_label} | Lag {lag_label}"
            ),
            supporting_text=dependency.relationship_label,
            meta_text=f"Linked task ID: {dependency.linked_task_id}",
            can_primary_action=False,
            can_secondary_action=False,
            state=state,
        )

    def _build_task_state(self, task) -> dict[str, object]:
        duration_value = task.duration_days if task.duration_days is not None else ""
        priority_value = task.priority if task.priority is not None else ""
        return {
            "taskId": task.id,
            "projectId": task.project_id,
            "projectName": task.project_name or "",
            "name": task.name,
            "description": task.description or "",
            "status": task.status,
            "statusLabel": task.status_label,
            "startDate": self._format_date(task.start_date),
            "startDateLabel": self._format_date_label(task.start_date),
            "endDate": self._format_date(task.end_date),
            "endDateLabel": self._format_date_label(task.end_date),
            "durationDays": str(duration_value),
            "durationLabel": (
                f"{duration_value} day(s)" if duration_value != "" else "Not set"
            ),
            "deadline": self._format_date(task.deadline),
            "deadlineLabel": self._format_date_label(task.deadline),
            "priority": str(priority_value),
            "priorityLabel": (
                str(priority_value) if priority_value != "" else "Not set"
            ),
            "percentComplete": f"{float(task.percent_complete or 0.0):.1f}",
            "percentCompleteLabel": f"{float(task.percent_complete or 0.0):.1f}%",
            "actualStart": self._format_date(task.actual_start),
            "actualStartLabel": self._format_date_label(task.actual_start),
            "actualEnd": self._format_date(task.actual_end),
            "actualEndLabel": self._format_date_label(task.actual_end),
            "version": task.version,
        }

    @staticmethod
    def _matches_search(task, search_text: str) -> bool:
        if not search_text:
            return True
        normalized_search = search_text.casefold()
        haystacks = (
            task.name or "",
            task.description or "",
            task.project_name or "",
        )
        return any(
            normalized_search in value.casefold()
            for value in haystacks
        )

    @staticmethod
    def _matches_status(task, status_filter: str) -> bool:
        if status_filter == "all":
            return True
        return task.status == status_filter

    @staticmethod
    def _resolve_project_id(
        project_id: str | None,
        project_options: tuple[TaskSelectorOptionViewModel, ...],
    ) -> str:
        normalized_id = (project_id or "").strip()
        option_values = {option.value for option in project_options}
        if normalized_id and normalized_id in option_values:
            return normalized_id
        if project_options:
            return project_options[0].value
        return ""

    @staticmethod
    def _resolve_task_id(selected_task_id: str | None, filtered_tasks) -> str:
        normalized_id = (selected_task_id or "").strip()
        if normalized_id and any(task.id == normalized_id for task in filtered_tasks):
            return normalized_id
        if filtered_tasks:
            return filtered_tasks[0].id
        return ""

    @staticmethod
    def _normalize_status_filter(
        status_filter: str,
        status_options: tuple[TaskSelectorOptionViewModel, ...],
    ) -> str:
        normalized_value = (status_filter or "all").strip().lower()
        available_values = {
            option.value.lower(): option.value
            for option in status_options
        }
        return available_values.get(normalized_value, "all")

    @staticmethod
    def _build_empty_state(
        *,
        project_options,
        all_tasks,
        filtered_tasks,
        search_text: str,
        status_filter: str,
    ) -> str:
        if not project_options:
            return "No projects are available yet. Create a project before planning tasks."
        if filtered_tasks:
            return ""
        if not all_tasks:
            return "No tasks are available for the selected project yet."
        if search_text or status_filter != "all":
            return "No tasks match the current filters."
        return "No tasks are available for the selected project yet."

    @staticmethod
    def _format_date(value: date | None) -> str:
        if value is None:
            return ""
        return value.isoformat()

    @staticmethod
    def _format_date_label(value: date | None) -> str:
        if value is None:
            return "Not set"
        return value.isoformat()

    @staticmethod
    def _require_text(payload: dict[str, Any], key: str, message: str) -> str:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            raise ValueError(message)
        return value

    @staticmethod
    def _optional_text(payload: dict[str, Any], key: str) -> str | None:
        value = str(payload.get(key, "") or "").strip()
        return value or None

    @staticmethod
    def _optional_int(payload: dict[str, Any], key: str) -> int | None:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            return None
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(
                f"{key.replace('_', ' ').replace('Days', ' days').title()} "
                "must be a whole number."
            ) from exc

    @staticmethod
    def _optional_float(payload: dict[str, Any], key: str) -> float | None:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            return None
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(
                f"{key.replace('Logged', ' logged').replace('_', ' ').title()} "
                "must be a valid number."
            ) from exc

    @classmethod
    def _require_float(
        cls,
        payload: dict[str, Any],
        key: str,
        message: str,
    ) -> float:
        value = cls._optional_float(payload, key)
        if value is None:
            raise ValueError(message)
        return value

    @staticmethod
    def _optional_date(payload: dict[str, Any], key: str) -> date | None:
        value = str(payload.get(key, "") or "").strip()
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                f"{key.replace('Date', ' date').replace('_', ' ').title()} "
                "must use YYYY-MM-DD."
            ) from exc


__all__ = ["ProjectTasksWorkspacePresenter"]
