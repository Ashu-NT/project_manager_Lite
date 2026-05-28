from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from src.core.modules.project_management.api.desktop import (
    AssignmentValidationDesktopDto,
    ProjectManagementCollaborationDesktopApi,
    ProjectManagementTasksDesktopApi,
    ProjectManagementTimesheetsDesktopApi,
    TaskCollaborationPostCommand,
    TaskAssignmentAllocationCommand,
    TaskAssignmentCreateCommand,
    TaskAssignmentHoursCommand,
    TaskBulkStatusCommand,
    TaskCreateCommand,
    TaskDependencyCreateCommand,
    TaskProgressCommand,
    TaskUpdateCommand,
    TimesheetEntryCreateCommand,
    TimesheetEntryUpdateCommand,
    build_project_management_collaboration_desktop_api,
    build_project_management_tasks_desktop_api,
    build_project_management_timesheets_desktop_api,
)
from src.ui_qml.modules.project_management.presenters.task_filters import (
    build_task_priority_options,
    build_task_schedule_options,
    matches_task_filters,
    normalize_task_filter,
)
from src.ui_qml.modules.project_management.view_models.collaboration import (
    CollaborationCollectionViewModel,
    CollaborationRecordViewModel,
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
from src.ui_qml.modules.project_management.view_models.timesheets import (
    TimesheetCollectionViewModel,
    TimesheetDetailFieldViewModel,
    TimesheetDetailViewModel,
    TimesheetRecordViewModel,
)

@dataclass(frozen=True)
class _TaskFilterOptions:
    project_options: tuple[TaskSelectorOptionViewModel, ...]
    status_options: tuple[TaskSelectorOptionViewModel, ...]
    bulk_status_options: tuple[TaskSelectorOptionViewModel, ...]
    priority_options: tuple[TaskSelectorOptionViewModel, ...]
    schedule_options: tuple[TaskSelectorOptionViewModel, ...]


@dataclass(frozen=True)
class _NormalizedTaskFilters:
    search_text: str
    status_filter: str
    priority_filter: str
    schedule_filter: str


@dataclass(frozen=True)
class _PagedTaskResult:
    items: tuple[Any, ...]
    total_count: int
    page: int
    page_size: int

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
            """
            Build the task list workspace.

            This method intentionally avoids loading heavy selected-task sections:
            assignments, dependencies, timesheets, and collaboration.

            Detail-page data should be loaded through build_task_detail_state().
            Time data should be loaded through build_task_time_state().
            Collaboration data should be loaded through build_task_collaboration_state().
            """
            options = self._build_task_filter_options()

            resolved_project_id = self._resolve_project_id(
                project_id,
                options.project_options,
            )

            filters = self._normalize_workspace_filters(
                search_text=search_text,
                status_filter=status_filter,
                priority_filter=priority_filter,
                schedule_filter=schedule_filter,
                status_options=options.status_options,
                priority_options=options.priority_options,
                schedule_options=options.schedule_options,
            )

            all_tasks = self._load_tasks_for_project(resolved_project_id)
            filtered_tasks = self._filter_tasks(all_tasks, filters)

            paged_tasks = self._paginate_tasks(
                filtered_tasks,
                page=page,
                page_size=page_size,
            )

            resolved_task_id = self._resolve_task_id(
                selected_task_id,
                filtered_tasks,
            )

            selected_task = self._find_task(filtered_tasks, resolved_task_id)

            return TaskCatalogWorkspaceViewModel(
                overview=self._build_overview(
                    all_tasks=all_tasks,
                    filtered_tasks=filtered_tasks,
                    collaboration_workspace_snapshot=None,
                    collaboration_snapshot=None,
                    has_selected_task=bool(resolved_task_id),
                ),
                project_options=options.project_options,
                selected_project_id=resolved_project_id,
                status_options=options.status_options,
                bulk_status_options=options.bulk_status_options,
                priority_options=options.priority_options,
                schedule_options=options.schedule_options,
                selected_status_filter=filters.status_filter,
                selected_priority_filter=filters.priority_filter,
                selected_schedule_filter=filters.schedule_filter,
                search_text=filters.search_text,
                tasks=tuple(
                    self._to_task_record_view_model(task)
                    for task in paged_tasks.items
                ),
                total_count=paged_tasks.total_count,
                page=paged_tasks.page,
                page_size=paged_tasks.page_size,
                selected_task_id=resolved_task_id,
                selected_task_detail=self._build_detail_view_model(
                    selected_task,
                    assignment_count=0,
                    dependency_count=0,
                ),
                empty_state=self._build_empty_state(
                    project_options=options.project_options,
                    all_tasks=all_tasks,
                    filtered_tasks=filtered_tasks,
                    search_text=filters.search_text,
                    status_filter=filters.status_filter,
                    priority_filter=filters.priority_filter,
                    schedule_filter=filters.schedule_filter,
                ),
            )

    def build_task_basic_detail_state(
        self,
        *,
        task_id: str,
        project_id: str | None = None,
    ) -> TaskCatalogWorkspaceViewModel:
        """
        Fastest detail state: only the selected task record.

        Skips assignments, dependencies, timesheets, and collaboration.
        Use this for activateTask so the detail page renders immediately.
        Assignments and dependencies load on demand via build_task_detail_state().
        """
        normalized_task_id = (task_id or "").strip()
        selected_task = self._resolve_selected_task(
            task_id=normalized_task_id,
            project_id=project_id,
        )

        if selected_task is None:
            return self._build_empty_task_detail_state(project_id=project_id)

        return TaskCatalogWorkspaceViewModel(
            overview=self._build_empty_overview(),
            selected_project_id=project_id or "",
            selected_task_id=normalized_task_id,
            selected_task_detail=self._build_detail_view_model(
                selected_task,
                assignment_count=0,
                dependency_count=0,
            ),
        )

    def build_task_detail_state(
        self,
        *,
        task_id: str,
        project_id: str | None = None,
    ) -> TaskCatalogWorkspaceViewModel:
        """
        Full detail state for one selected task.

        Loads:
        - selected task detail

        Does not load:
        - assignments
        - dependencies
        - timesheets
        - collaboration comments
        - collaboration presence
        """
        normalized_task_id = (task_id or "").strip()
        selected_task = self._resolve_selected_task(
            task_id=normalized_task_id,
            project_id=project_id,
        )

        if selected_task is None:
            return self._build_empty_task_detail_state(project_id=project_id)

        return TaskCatalogWorkspaceViewModel(
            overview=self._build_empty_overview(),
            selected_project_id=project_id or "",
            selected_task_id=normalized_task_id,
            selected_task_detail=self._build_detail_view_model(
                selected_task,
                assignment_count=0,
                dependency_count=0,
            ),
        )

    def build_task_assignments_state(
        self,
        *,
        task_id: str,
        project_id: str | None = None,
    ) -> TaskCatalogWorkspaceViewModel:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            return TaskCatalogWorkspaceViewModel(
                overview=self._build_empty_overview(),
                selected_project_id=project_id or "",
                selected_task_id="",
                assignment_options=(),
                assignments=self._build_assignments_collection(
                    selected_task=None,
                    assignments=(),
                    assignment_options=(),
                ),
            )

        selected_task = self._resolve_selected_task(
            task_id=normalized_task_id,
            project_id=project_id,
        )
        if selected_task is None:
            return TaskCatalogWorkspaceViewModel(
                overview=self._build_empty_overview(),
                selected_project_id=project_id or "",
                selected_task_id="",
                assignment_options=(),
                assignments=self._build_assignments_collection(
                    selected_task=None,
                    assignments=(),
                    assignment_options=(),
                ),
            )

        assignments = self._desktop_api.list_assignments(normalized_task_id)
        assignment_options = self._build_assignment_options(
            selected_task.project_id or project_id,
        )
        return TaskCatalogWorkspaceViewModel(
            overview=self._build_empty_overview(),
            selected_project_id=project_id or "",
            selected_task_id=normalized_task_id,
            assignment_options=assignment_options,
            assignments=self._build_assignments_collection(
                selected_task=selected_task,
                assignments=assignments,
                assignment_options=assignment_options,
            ),
        )

    def build_task_dependencies_state(
        self,
        *,
        task_id: str,
        project_id: str | None = None,
    ) -> TaskCatalogWorkspaceViewModel:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            return TaskCatalogWorkspaceViewModel(
                overview=self._build_empty_overview(),
                selected_project_id=project_id or "",
                selected_task_id="",
                dependency_task_options=(),
                dependency_type_options=(),
                dependencies=self._build_dependencies_collection(
                    selected_task=None,
                    all_tasks=(),
                    dependencies=(),
                ),
            )

        selected_task = self._resolve_selected_task(
            task_id=normalized_task_id,
            project_id=project_id,
        )
        if selected_task is None:
            return TaskCatalogWorkspaceViewModel(
                overview=self._build_empty_overview(),
                selected_project_id=project_id or "",
                selected_task_id="",
                dependency_task_options=(),
                dependency_type_options=(),
                dependencies=self._build_dependencies_collection(
                    selected_task=None,
                    all_tasks=(),
                    dependencies=(),
                ),
            )

        dependencies = self._desktop_api.list_dependencies(normalized_task_id)
        all_tasks = self._load_tasks_for_project(selected_task.project_id)
        dependency_type_options = self._build_dependency_type_options()
        dependency_task_options = self._build_dependency_task_options(
            all_tasks,
            selected_task_id=normalized_task_id,
        )
        return TaskCatalogWorkspaceViewModel(
            overview=self._build_empty_overview(),
            selected_project_id=project_id or "",
            selected_task_id=normalized_task_id,
            dependency_task_options=dependency_task_options,
            dependency_type_options=dependency_type_options,
            dependencies=self._build_dependencies_collection(
                selected_task=selected_task,
                all_tasks=all_tasks,
                dependencies=dependencies,
            ),
        )

    def build_task_time_state(
        self,
        *,
        task_id: str,
        selected_assignment_id: str | None = None,
        selected_time_period_start: str = "",
        selected_time_entry_id: str | None = None,
    ) -> TaskCatalogWorkspaceViewModel:
        normalized_task_id = (task_id or "").strip()

        assignments = tuple(
            self._desktop_api.list_assignments(normalized_task_id)
            if normalized_task_id
            else ()
        )
        assignment_options = self._build_time_assignment_options(assignments)

        resolved_assignment_id = self._resolve_assignment_id(
            selected_assignment_id,
            assignments,
        )

        timesheet_snapshot = (
            self._timesheets_desktop_api.build_assignment_snapshot(
                resolved_assignment_id,
                period_start=self._optional_iso_date(selected_time_period_start),
            )
            if resolved_assignment_id
            else None
        )

        time_period_options = tuple(
            TaskSelectorOptionViewModel(value=option.value, label=option.label)
            for option in (
                timesheet_snapshot.period_options
                if timesheet_snapshot is not None
                else ()
            )
        )

        resolved_time_period_start = (
            timesheet_snapshot.selected_period_start
            if timesheet_snapshot is not None
            else ""
        )

        resolved_time_entry_id = self._resolve_time_entry_id(
            selected_time_entry_id,
            timesheet_snapshot.entries if timesheet_snapshot is not None else (),
        )

        selected_time_entry = next(
            (
                entry
                for entry in (
                    timesheet_snapshot.entries
                    if timesheet_snapshot is not None
                    else ()
                )
                if entry.entry_id == resolved_time_entry_id
            ),
            None,
        )

        return TaskCatalogWorkspaceViewModel(
            overview=self._build_empty_overview(),
            selected_task_id=normalized_task_id,
            assignment_options=assignment_options,
            selected_assignment_id=resolved_assignment_id,
            time_period_options=time_period_options,
            selected_time_period_start=resolved_time_period_start,
            time_assignment_summary=self._build_time_assignment_summary(
                timesheet_snapshot
            ),
            time_entries=self._build_time_entries_collection(timesheet_snapshot),
            selected_time_entry_id=resolved_time_entry_id,
            selected_time_entry_detail=self._build_selected_time_entry_detail(
                selected_time_entry
            ),
        )

    def build_empty_task_time_state(self) -> TaskCatalogWorkspaceViewModel:
        return TaskCatalogWorkspaceViewModel(
            overview=self._build_empty_overview(),
            selected_assignment_id="",
            selected_time_period_start="",
            selected_time_entry_id="",
            time_period_options=(),
            time_assignment_summary=self._build_time_assignment_summary(None),
            time_entries=self._build_time_entries_collection(None),
            selected_time_entry_detail=self._build_selected_time_entry_detail(None),
        )

    def build_task_collaboration_state(
        self,
        *,
        task_id: str,
    ) -> TaskCatalogWorkspaceViewModel:
        """
        Build only the collaboration section for a selected task.
        """
        normalized_task_id = (task_id or "").strip()

        selected_task = self._desktop_api.get_task(normalized_task_id) if normalized_task_id else None

        collaboration_snapshot = (
            self._collaboration_desktop_api.build_task_snapshot(normalized_task_id)
            if normalized_task_id
            else None
        )

        return TaskCatalogWorkspaceViewModel(
            overview=self._build_empty_overview(),
            selected_task_id=normalized_task_id if selected_task is not None else "",
            collaboration_mention_options=tuple(
                TaskSelectorOptionViewModel(value=option.value, label=option.label)
                for option in (
                    collaboration_snapshot.mention_options
                    if collaboration_snapshot is not None
                    else ()
                )
            ),
            collaboration_document_options=tuple(
                TaskSelectorOptionViewModel(value=option.value, label=option.label)
                for option in (
                    collaboration_snapshot.document_options
                    if collaboration_snapshot is not None
                    else ()
                )
            ),
            collaboration_comments=self._build_collaboration_comments_collection(
                selected_task=selected_task,
                snapshot=collaboration_snapshot,
            ),
            collaboration_presence=self._build_collaboration_presence_collection(
                selected_task=selected_task,
                snapshot=collaboration_snapshot,
            ),
        )

    def build_task_schedule_impact_state(
        self,
        *,
        task_id: str,
        project_id: str | None = None,
    ) -> dict[str, object]:
        normalized_task_id = (task_id or "").strip()
        normalized_project_id = (project_id or "").strip()
        if not normalized_task_id or not normalized_project_id:
            return {
                "available": False,
                "taskId": normalized_task_id,
                "summary": "Select a task with a project to view schedule impact.",
                "rows": [],
                "affectedCount": 0,
                "maxProjectFinishShiftDays": 0,
                "requiresApproval": False,
                "approvalLabel": "",
                "newlyCriticalCount": 0,
                "noLongerCriticalCount": 0,
            }
        try:
            report = self._desktop_api.get_schedule_impact(
                normalized_task_id, normalized_project_id
            )
        except Exception:
            return {
                "available": False,
                "taskId": normalized_task_id,
                "summary": "Schedule impact analysis is unavailable.",
                "rows": [],
                "affectedCount": 0,
                "maxProjectFinishShiftDays": 0,
                "requiresApproval": False,
                "approvalLabel": "",
                "newlyCriticalCount": 0,
                "noLongerCriticalCount": 0,
            }
        if not report.is_available:
            return {
                "available": False,
                "taskId": normalized_task_id,
                "summary": (
                    "Schedule impact analysis requires the task to have a start date "
                    "and a connected scheduling service."
                ),
                "rows": [],
                "affectedCount": 0,
                "maxProjectFinishShiftDays": 0,
                "requiresApproval": False,
                "approvalLabel": "",
                "newlyCriticalCount": 0,
                "noLongerCriticalCount": 0,
            }
        project_shift = int(report.max_project_finish_shift_days or 0)
        if project_shift > 0:
            shift_label = f"Project finish would slip by {project_shift} working day(s)."
        elif project_shift < 0:
            shift_label = f"Project finish would improve by {abs(project_shift)} working day(s)."
        else:
            shift_label = "Project finish would not change."
        summary = (
            f"Simulating 1-day start slip: {report.affected_count} task(s) affected. "
            + shift_label
        )
        newly_critical = int(len(report.newly_critical_task_ids))
        no_longer_critical = int(len(report.no_longer_critical_task_ids))
        rows = [
            {
                "taskId": task.task_id,
                "taskName": task.task_name,
                "startShift": self._shift_days_label(task.start_shift_days),
                "finishShift": self._shift_days_label(task.finish_shift_days),
                "startShiftDays": task.start_shift_days,
                "finishShiftDays": task.finish_shift_days,
                "isCritical": task.is_critical,
                "criticalLabel": "Critical" if task.is_critical else "Non-critical",
                "isChanged": task.task_id == normalized_task_id,
            }
            for task in report.affected_tasks
        ]
        return {
            "available": True,
            "taskId": normalized_task_id,
            "summary": summary,
            "rows": rows,
            "affectedCount": report.affected_count,
            "maxProjectFinishShiftDays": project_shift,
            "requiresApproval": report.requires_approval,
            "approvalLabel": "Approval required" if report.requires_approval else "",
            "newlyCriticalCount": newly_critical,
            "noLongerCriticalCount": no_longer_critical,
        }

    @staticmethod
    def _shift_days_label(days: int) -> str:
        if days == 0:
            return "No change"
        if days > 0:
            return f"+{days}d"
        return f"{days}d"

    def build_task_skill_requirements_state(
        self,
        *,
        task_id: str,
    ) -> TaskCatalogWorkspaceViewModel:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            return TaskCatalogWorkspaceViewModel(
                overview=self._build_empty_overview(),
                task_skill_requirements=self._build_skill_requirements_collection(
                    None, ()
                ),
            )
        reqs = self._desktop_api.list_task_skill_requirements(normalized_task_id)
        return TaskCatalogWorkspaceViewModel(
            overview=self._build_empty_overview(),
            selected_task_id=normalized_task_id,
            task_skill_requirements=self._build_skill_requirements_collection(
                normalized_task_id, reqs
            ),
        )

    @staticmethod
    def _build_skill_requirements_collection(
        task_id: str | None,
        requirements,
    ) -> TaskExecutionCollectionViewModel:
        if task_id is None:
            return TaskExecutionCollectionViewModel(
                title="Skill Requirements",
                subtitle=(
                    "Skills and certifications required to assign resources to this task."
                ),
                empty_state=(
                    "Select a task to review skill and certification requirements."
                ),
            )
        if requirements:
            return TaskExecutionCollectionViewModel(
                title="Skill Requirements",
                subtitle="Skills and certifications required for resource assignment.",
                items=tuple(
                    ProjectTasksWorkspacePresenter._to_skill_requirement_record_view_model(req)
                    for req in requirements
                ),
            )
        return TaskExecutionCollectionViewModel(
            title="Skill Requirements",
            subtitle="Skills and certifications required for resource assignment.",
            empty_state="No skill or certification requirements are linked to this task.",
        )

    @staticmethod
    def _to_skill_requirement_record_view_model(req) -> TaskRecordViewModel:
        skill_code = str(getattr(req, "skill_code", "") or "")
        cert_code = str(getattr(req, "certification_code", "") or "")
        code = skill_code or cert_code
        req_type = str(getattr(req, "requirement_type", "") or "")
        req_type_label = "Certification" if req_type == "certification" else "Skill"
        proficiency_label = str(getattr(req, "required_proficiency_label", "") or "")
        mode_label = str(getattr(req, "validation_mode_label", "") or "")
        notes = str(getattr(req, "notes", "") or "")
        state = {
            "requirementId": str(getattr(req, "id", "") or ""),
            "taskId": str(getattr(req, "task_id", "") or ""),
            "skillCode": skill_code,
            "certificationCode": cert_code,
            "requirementType": req_type,
            "requiredProficiency": str(getattr(req, "required_proficiency", "") or ""),
            "requiredProficiencyLabel": proficiency_label,
            "validationMode": str(getattr(req, "validation_mode", "") or ""),
            "validationModeLabel": mode_label,
            "notes": notes,
        }
        return TaskRecordViewModel(
            id=str(getattr(req, "id", "") or ""),
            title=code or "Unknown",
            status_label=proficiency_label,
            subtitle=f"{req_type_label} | Mode: {mode_label}",
            supporting_text=notes if notes else "No notes recorded.",
            meta_text=f"Validation: {mode_label}",
            can_primary_action=False,
            can_secondary_action=False,
            can_tertiary_action=False,
            state=state,
        )

    def _build_task_filter_options(self) -> _TaskFilterOptions:
        project_options = (
            TaskSelectorOptionViewModel(value="", label="All Projects"),
            *(
                TaskSelectorOptionViewModel(value=option.value, label=option.label)
                for option in self._desktop_api.list_projects()
            ),
        )

        raw_status_options = tuple(self._desktop_api.list_statuses())

        status_options = (
            TaskSelectorOptionViewModel(value="all", label="All statuses"),
            *(
                TaskSelectorOptionViewModel(value=option.value, label=option.label)
                for option in raw_status_options
            ),
        )

        bulk_status_options = tuple(
            TaskSelectorOptionViewModel(value=option.value, label=option.label)
            for option in raw_status_options
        )

        return _TaskFilterOptions(
            project_options=project_options,
            status_options=status_options,
            bulk_status_options=bulk_status_options,
            priority_options=build_task_priority_options(),
            schedule_options=build_task_schedule_options(),
        )

    def _normalize_workspace_filters(
        self,
        *,
        search_text: str,
        status_filter: str,
        priority_filter: str,
        schedule_filter: str,
        status_options: tuple[TaskSelectorOptionViewModel, ...],
        priority_options: tuple[TaskSelectorOptionViewModel, ...],
        schedule_options: tuple[TaskSelectorOptionViewModel, ...],
    ) -> _NormalizedTaskFilters:
        return _NormalizedTaskFilters(
            search_text=(search_text or "").strip(),
            status_filter=self._normalize_status_filter(
                status_filter,
                status_options,
            ),
            priority_filter=normalize_task_filter(
                priority_filter,
                priority_options,
            ),
            schedule_filter=normalize_task_filter(
                schedule_filter,
                schedule_options,
            ),
        )

    def _load_tasks_for_project(self, project_id: str | None):
        normalized_project_id = (project_id or "").strip()

        if normalized_project_id:
            return self._desktop_api.list_tasks(normalized_project_id)

        return self._desktop_api.list_all_tasks()

    @staticmethod
    def _filter_tasks(
        all_tasks,
        filters: _NormalizedTaskFilters,
    ):
        return tuple(
            task
            for task in all_tasks
            if matches_task_filters(
                task,
                search_text=filters.search_text,
                status_filter=filters.status_filter,
                priority_filter=filters.priority_filter,
                schedule_filter=filters.schedule_filter,
            )
        )

    @staticmethod
    def _paginate_tasks(
        tasks,
        *,
        page: int,
        page_size: int,
    ) -> _PagedTaskResult:
        total_count = len(tasks)
        resolved_page = max(1, page)
        resolved_page_size = max(1, page_size)
        offset = (resolved_page - 1) * resolved_page_size

        return _PagedTaskResult(
            items=tasks[offset: offset + resolved_page_size],
            total_count=total_count,
            page=resolved_page,
            page_size=resolved_page_size,
        )

    @staticmethod
    def _find_task(tasks, task_id: str | None):
        normalized_task_id = (task_id or "").strip()

        if not normalized_task_id:
            return None

        return next(
            (task for task in tasks if task.id == normalized_task_id),
            None,
        )

    def _build_assignment_options(
        self,
        project_id: str | None,
    ) -> tuple[TaskSelectorOptionViewModel, ...]:
        try:
            options = self._desktop_api.list_project_resources(project_id)
        except Exception:
            return ()
        return tuple(
            TaskSelectorOptionViewModel(value=option.value, label=option.label)
            for option in options
        )

    def _resolve_selected_task(
        self,
        *,
        task_id: str,
        project_id: str | None = None,
    ):
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            return None
        normalized_project_id = (project_id or "").strip()
        if normalized_project_id:
            try:
                selected_task = self._find_task(
                    self._load_tasks_for_project(normalized_project_id),
                    normalized_task_id,
                )
            except Exception:
                selected_task = None
            if selected_task is not None:
                return selected_task
        return self._desktop_api.get_task(normalized_task_id)

    def _build_dependency_type_options(
        self,
    ) -> tuple[TaskSelectorOptionViewModel, ...]:
        return tuple(
            TaskSelectorOptionViewModel(value=option.value, label=option.label)
            for option in self._desktop_api.list_dependency_types()
        )

    @staticmethod
    def _build_time_assignment_options(
        assignments,
    ) -> tuple[TaskSelectorOptionViewModel, ...]:
        options: list[TaskSelectorOptionViewModel] = []
        for assignment in assignments:
            resource_name = str(getattr(assignment, "resource_name", "") or getattr(assignment, "resource_id", "") or "Assignment")
            allocation_percent = float(getattr(assignment, "allocation_percent", 0.0) or 0.0)
            label = (
                f"{resource_name} | {allocation_percent:g}% allocation"
                if allocation_percent > 0
                else resource_name
            )
            options.append(
                TaskSelectorOptionViewModel(
                    value=str(getattr(assignment, "id", "") or ""),
                    label=label,
                )
            )
        return tuple(options)

    @staticmethod
    def _build_dependency_task_options(
        all_tasks,
        *,
        selected_task_id: str,
    ) -> tuple[TaskSelectorOptionViewModel, ...]:
        return tuple(
            TaskSelectorOptionViewModel(value=task.id, label=task.name)
            for task in all_tasks
            if task.id != selected_task_id
        )

    @staticmethod
    def _build_empty_overview() -> TaskCatalogOverviewViewModel:
        return TaskCatalogOverviewViewModel(
            title="Tasks",
            subtitle=(
                "Task planning, progress, dependencies, assignments, "
                "and execution state."
            ),
            metrics=(),
        )

    def _build_empty_task_detail_state(
        self,
        *,
        project_id: str | None,
    ) -> TaskCatalogWorkspaceViewModel:
        return TaskCatalogWorkspaceViewModel(
            overview=self._build_empty_overview(),
            selected_project_id=project_id or "",
            selected_task_id="",
            selected_task_detail=self._build_detail_view_model(
                None,
                assignment_count=0,
                dependency_count=0,
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

    def add_task_time_entry(self, payload: dict[str, Any]) -> None:
        command = TimesheetEntryCreateCommand(
            assignment_id=self._require_text(
                payload,
                "assignmentId",
                "Choose an assignment before logging time.",
            ),
            entry_date=self._require_date(
                payload,
                "entryDate",
                "Entry date is required.",
            ),
            hours=self._require_float(
                payload,
                "hours",
                "Hours are required.",
            ),
            note=self._optional_text(payload, "note") or "",
        )
        self._timesheets_desktop_api.add_time_entry(command)

    def update_task_time_entry(self, payload: dict[str, Any]) -> None:
        command = TimesheetEntryUpdateCommand(
            entry_id=self._require_text(
                payload,
                "entryId",
                "Choose an entry to update.",
            ),
            entry_date=self._require_date(
                payload,
                "entryDate",
                "Entry date is required.",
            ),
            hours=self._require_float(
                payload,
                "hours",
                "Hours are required.",
            ),
            note=self._optional_text(payload, "note") or "",
        )
        self._timesheets_desktop_api.update_time_entry(command)

    def delete_task_time_entry(self, entry_id: str) -> None:
        normalized_entry_id = (entry_id or "").strip()
        if not normalized_entry_id:
            raise ValueError("Choose an entry to delete.")
        self._timesheets_desktop_api.delete_time_entry(normalized_entry_id)

    def submit_task_period(self, payload: dict[str, Any]) -> None:
        self._timesheets_desktop_api.submit_period(
            resource_id=self._require_text(
                payload,
                "resourceId",
                "Choose a resource period to submit.",
            ),
            period_start=self._require_date(
                payload,
                "periodStart",
                "Period start is required.",
            ),
            note=self._optional_text(payload, "note") or "",
        )

    def lock_task_period(self, payload: dict[str, Any]) -> None:
        self._timesheets_desktop_api.lock_period(
            resource_id=self._require_text(
                payload,
                "resourceId",
                "Choose a resource period to lock.",
            ),
            period_start=self._require_date(
                payload,
                "periodStart",
                "Period start is required.",
            ),
            note=self._optional_text(payload, "note") or "",
        )

    def unlock_task_period(self, payload: dict[str, Any]) -> None:
        self._timesheets_desktop_api.unlock_period(
            self._require_text(
                payload,
                "periodId",
                "Choose a period to unlock.",
            ),
            note=self._optional_text(payload, "note") or "",
        )

    def delete_assignment(self, assignment_id: str) -> None:
        normalized_assignment_id = (assignment_id or "").strip()
        if not normalized_assignment_id:
            raise ValueError("Assignment ID is required to remove an assignment.")
        self._desktop_api.delete_assignment(normalized_assignment_id)

    def apply_bulk_status(self, payload: dict[str, Any]) -> None:
        task_ids = tuple(self._coerce_string_list(payload.get("taskIds")))
        if not task_ids:
            raise ValueError("Select one or more tasks first.")
        target_status = self._require_text(
            payload,
            "status",
            "Choose a valid target status.",
        )
        reopen_percent_complete = None
        if str(target_status or "").strip().upper() == "IN_PROGRESS":
            reopen_percent_complete = self._optional_float(
                payload,
                "reopenPercentComplete",
            )
        changed_tasks = self._desktop_api.apply_bulk_status(
            TaskBulkStatusCommand(
                task_ids=task_ids,
                status=target_status,
                reopen_percent_complete=reopen_percent_complete,
            )
        )
        if not changed_tasks:
            raise ValueError("Selected tasks already have this status.")

    def bulk_delete_tasks(self, task_ids: list[str] | tuple[str, ...]) -> None:
        normalized_ids = tuple(self._coerce_string_list(task_ids))
        if not normalized_ids:
            raise ValueError("Select one or more tasks first.")
        deleted_ids = self._desktop_api.delete_tasks(normalized_ids)
        if not deleted_ids:
            raise ValueError("No selected tasks could be deleted.")

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

    def post_task_comment(self, payload: dict[str, Any]) -> None:
        command = TaskCollaborationPostCommand(
            task_id=self._require_text(
                payload,
                "taskId",
                "Select a task before posting a collaboration update.",
            ),
            body=self._require_text(
                payload,
                "body",
                "Comment text is required.",
            ),
            attachments=tuple(self._coerce_string_list(payload.get("attachments"))),
            linked_document_ids=tuple(
                self._coerce_string_list(payload.get("linkedDocumentIds"))
            ),
        )
        self._collaboration_desktop_api.post_task_comment(command)

    def mark_task_collaboration_read(self, task_id: str) -> None:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            raise ValueError("Select a task before marking collaboration updates as read.")
        self._collaboration_desktop_api.mark_task_mentions_read(normalized_task_id)

    def touch_task_collaboration_presence(
        self,
        task_id: str,
        *,
        activity: str = "reviewing",
    ) -> None:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            raise ValueError("Select a task before starting a presence session.")
        normalized_activity = (activity or "").strip() or "reviewing"
        self._collaboration_desktop_api.touch_task_presence(
            normalized_task_id,
            activity=normalized_activity,
        )

    def clear_task_collaboration_presence(self, task_id: str) -> None:
        normalized_task_id = (task_id or "").strip()
        if not normalized_task_id:
            return
        self._collaboration_desktop_api.clear_task_presence(normalized_task_id)

    @staticmethod
    def _build_overview(
        *,
        all_tasks,
        filtered_tasks,
        collaboration_workspace_snapshot,
        collaboration_snapshot,
        has_selected_task: bool,
    ) -> TaskCatalogOverviewViewModel:
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
        unread_mentions_count = sum(
            1
            for item in getattr(collaboration_workspace_snapshot, "inbox", ())
            if bool(getattr(item, "unread", False))
        )
        notification_count = len(
            getattr(collaboration_workspace_snapshot, "notifications", ())
        )
        active_presence_count = len(
            getattr(collaboration_snapshot, "active_presence", ())
            if collaboration_snapshot is not None
            else ()
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
                TaskCatalogMetricViewModel(
                    label="Mentions",
                    value=str(unread_mentions_count),
                    supporting_text="Unread task mentions across accessible projects.",
                ),
                TaskCatalogMetricViewModel(
                    label="Notifications",
                    value=str(notification_count),
                    supporting_text="Workflow alerts from approvals, timesheets, and mentions.",
                ),
                TaskCatalogMetricViewModel(
                    label="Active now",
                    value=str(active_presence_count),
                    supporting_text=(
                        "People currently active on the selected task."
                        if has_selected_task
                        else "Select a task to see active collaborators."
                    ),
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
        state.update(self._build_material_demand_state(task.id))
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
                    label="Material Demand",
                    value=str(state.get("materialDemandLabel", "No reservations")),
                    supporting_text=(
                        "Inventory-linked reservations and procurement demand for this task."
                    ),
                ),
                TaskDetailFieldViewModel(
                    label="Version",
                    value=str(state["version"]),
                ),
            ),
            state=state,
        )

    def _build_material_demand_state(self, task_id: str) -> dict[str, object]:
        normalized_task_id = str(task_id or "").strip()
        if not normalized_task_id:
            return {
                "materialDemandLabel": "No reservations",
                "materialDemandTotal": "0",
                "materialDemandActive": "0",
                "materialDemandFulfilled": "0",
                "materialDemandCancelled": "0",
            }
        try:
            summary = self._desktop_api.get_task_material_demand(normalized_task_id)
        except Exception:
            return {
                "materialDemandLabel": "Unavailable",
                "materialDemandTotal": "0",
                "materialDemandActive": "0",
                "materialDemandFulfilled": "0",
                "materialDemandCancelled": "0",
            }
        total_reserved = int(getattr(summary, "total_reserved", 0) or 0)
        active_count = int(getattr(summary, "active_count", 0) or 0)
        fulfilled_count = int(getattr(summary, "fulfilled_count", 0) or 0)
        cancelled_count = int(getattr(summary, "cancelled_count", 0) or 0)
        if total_reserved > 0:
            label = f"{active_count} active / {total_reserved} total"
        else:
            label = "No reservations"
        return {
            "materialDemandLabel": label,
            "materialDemandTotal": str(total_reserved),
            "materialDemandActive": str(active_count),
            "materialDemandFulfilled": str(fulfilled_count),
            "materialDemandCancelled": str(cancelled_count),
        }

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

    @staticmethod
    def _build_time_assignment_summary(snapshot) -> TimesheetDetailViewModel:
        if snapshot is None:
            return TimesheetDetailViewModel(
                title="No assignment selected",
                empty_state="Select a task assignment to review detailed time entries, period status, and labor totals.",
            )
        summary = snapshot.period_summary
        return TimesheetDetailViewModel(
            id=snapshot.assignment.value,
            title=snapshot.assignment.label,
            status_label=summary.status_label,
            subtitle=f"{summary.period_start_label} -> {summary.period_end_label}",
            description=snapshot.scope_summary,
            fields=(
                TimesheetDetailFieldViewModel(
                    label="Resource",
                    value=summary.resource_name,
                ),
                TimesheetDetailFieldViewModel(
                    label="Hours",
                    value=summary.total_hours_label,
                    supporting_text=f"{summary.entry_count} entry or entries in the selected resource month.",
                ),
                TimesheetDetailFieldViewModel(
                    label="Submitted by",
                    value=summary.submitted_by_username,
                    supporting_text=summary.submitted_at_label,
                ),
                TimesheetDetailFieldViewModel(
                    label="Decision",
                    value=summary.decided_by_username,
                    supporting_text=summary.decided_at_label,
                ),
                TimesheetDetailFieldViewModel(
                    label="Decision note",
                    value=summary.decision_note or "No review note recorded.",
                ),
            ),
            state={
                "assignmentId": snapshot.assignment.value,
                "resourceId": summary.resource_id,
                "periodStart": snapshot.selected_period_start,
                "periodId": summary.period_id,
                "projectId": snapshot.assignment.project_id,
            },
        )

    @classmethod
    def _build_time_entries_collection(cls, snapshot) -> TimesheetCollectionViewModel:
        if snapshot is None:
            return TimesheetCollectionViewModel(
                title="Time Entries",
                subtitle="Detailed labor entries for the selected task assignment.",
                empty_state="Select a task assignment to review or capture labor entries.",
            )
        return TimesheetCollectionViewModel(
            title="Time Entries",
            subtitle="Detailed labor entries for the selected task assignment.",
            empty_state="No time entries are available yet for the selected period.",
            items=tuple(
                cls._to_time_entry_record_view_model(entry)
                for entry in snapshot.entries
            ),
        )

    @staticmethod
    def _build_selected_time_entry_detail(selected_entry) -> TimesheetDetailViewModel:
        if selected_entry is None:
            return TimesheetDetailViewModel(
                title="No entry selected",
                empty_state="Select an entry from the period list to review or edit its captured labor note.",
            )
        return TimesheetDetailViewModel(
            id=selected_entry.entry_id,
            title=selected_entry.entry_date_label,
            status_label=selected_entry.hours_label,
            subtitle=selected_entry.author_username,
            description=selected_entry.note or "No labor note recorded.",
            fields=(
                TimesheetDetailFieldViewModel(label="Date", value=selected_entry.entry_date_label),
                TimesheetDetailFieldViewModel(label="Hours", value=selected_entry.hours_label),
                TimesheetDetailFieldViewModel(label="Author", value=selected_entry.author_username),
            ),
            state={
                "entryId": selected_entry.entry_id,
                "entryDate": selected_entry.entry_date_label,
                "hours": str(selected_entry.hours),
                "note": selected_entry.note,
            },
        )

    def _build_collaboration_comments_collection(
        self,
        *,
        selected_task,
        snapshot,
    ) -> CollaborationCollectionViewModel:
        if selected_task is None:
            return CollaborationCollectionViewModel(
                title="Task Collaboration",
                subtitle="Comments, mentions, attachments, and linked shared documents for the selected task.",
                empty_state="Select a task to review collaboration updates and post comments.",
            )
        if snapshot is None or not snapshot.comments:
            return CollaborationCollectionViewModel(
                title="Task Collaboration",
                subtitle="Comments, mentions, attachments, and linked shared documents for the selected task.",
                empty_state="No collaboration updates are linked to the selected task yet.",
            )
        return CollaborationCollectionViewModel(
            title="Task Collaboration",
            subtitle="Comments, mentions, attachments, and linked shared documents for the selected task.",
            items=tuple(
                self._to_collaboration_comment_record_view_model(comment)
                for comment in snapshot.comments
            ),
            empty_state="",
        )

    def _build_collaboration_presence_collection(
        self,
        *,
        selected_task,
        snapshot,
    ) -> CollaborationCollectionViewModel:
        if selected_task is None:
            return CollaborationCollectionViewModel(
                title="Active Presence",
                subtitle="People currently reviewing or updating the selected task.",
                empty_state="Select a task to review active collaboration presence.",
            )
        if snapshot is None or not snapshot.active_presence:
            return CollaborationCollectionViewModel(
                title="Active Presence",
                subtitle="People currently reviewing or updating the selected task.",
                empty_state="No active collaborators are visible for the selected task right now.",
            )
        return CollaborationCollectionViewModel(
            title="Active Presence",
            subtitle="People currently reviewing or updating the selected task.",
            items=tuple(
                self._to_collaboration_presence_record_view_model(item)
                for item in snapshot.active_presence
            ),
            empty_state="",
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

    @staticmethod
    def _to_time_entry_record_view_model(entry) -> TimesheetRecordViewModel:
        return TimesheetRecordViewModel(
            id=entry.entry_id,
            title=entry.entry_date_label,
            status_label=entry.hours_label,
            subtitle=entry.author_username,
            supporting_text=entry.note or "No labor note recorded.",
            meta_text=f"Assignment entry {entry.entry_id}",
            state={
                "entryId": entry.entry_id,
                "entryDate": entry.entry_date_label,
                "hours": entry.hours,
                "note": entry.note,
            },
        )

    @staticmethod
    def _to_collaboration_comment_record_view_model(
        comment,
    ) -> CollaborationRecordViewModel:
        meta_parts = [comment.created_at_label]
        if comment.mentions:
            meta_parts.append(f"Mentions: {comment.mentions_label}")
        if comment.linked_documents:
            meta_parts.append(f"Linked: {comment.linked_documents_label}")
        elif comment.attachments:
            meta_parts.append(f"Attachments: {comment.attachments_label}")
        return CollaborationRecordViewModel(
            id=comment.comment_id,
            title=f"@{comment.author_username}",
            status_label="Mentions" if comment.mentions else "Comment",
            subtitle=comment.body,
            supporting_text=(
                f"Attachments: {comment.attachments_label}"
                if comment.attachments
                else "No attachment references recorded."
            ),
            meta_text=" | ".join(part for part in meta_parts if part),
            state={
                "taskId": comment.task_id,
                "commentId": comment.comment_id,
                "mentions": list(comment.mentions),
                "attachments": list(comment.attachments),
                "linkedDocuments": list(comment.linked_documents),
            },
        )

    @staticmethod
    def _to_collaboration_presence_record_view_model(
        presence,
    ) -> CollaborationRecordViewModel:
        return CollaborationRecordViewModel(
            id=f"{presence.task_id}:{presence.username}",
            title=presence.who_label,
            status_label=presence.activity_label,
            subtitle=f"Last seen {presence.last_seen_at_label}",
            supporting_text="You are included in this presence view." if presence.is_self else "",
            meta_text=f"@{presence.username}" if presence.username else "",
            state={
                "taskId": presence.task_id,
                "username": presence.username,
                "isSelf": presence.is_self,
            },
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
    def _resolve_project_id(
        project_id: str | None,
        project_options: tuple[TaskSelectorOptionViewModel, ...],
    ) -> str:
        normalized_id = (project_id or "").strip()
        option_values = {option.value for option in project_options}
        if normalized_id in option_values:
            return normalized_id
        return ""  # default to all projects

    @staticmethod
    def _resolve_task_id(selected_task_id: str | None, filtered_tasks) -> str:
        normalized_id = (selected_task_id or "").strip()
        if normalized_id and any(task.id == normalized_id for task in filtered_tasks):
            return normalized_id
        if filtered_tasks:
            return filtered_tasks[0].id
        return ""

    @staticmethod
    def _resolve_assignment_id(selected_assignment_id: str | None, assignments) -> str:
        normalized_id = (selected_assignment_id or "").strip()
        available_values = [str(assignment.id or "") for assignment in assignments]
        if normalized_id and normalized_id in available_values:
            return normalized_id
        return available_values[0] if available_values else ""

    @staticmethod
    def _resolve_time_entry_id(selected_time_entry_id: str | None, entries) -> str:
        normalized_id = (selected_time_entry_id or "").strip()
        available_values = [str(entry.entry_id or "") for entry in entries]
        if normalized_id and normalized_id in available_values:
            return normalized_id
        return available_values[0] if available_values else ""

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
        priority_filter: str,
        schedule_filter: str,
    ) -> str:
        if not project_options:
            return "No projects are available yet. Create a project before planning tasks."
        if filtered_tasks:
            return ""
        if not all_tasks:
            return "No tasks are available for the selected project yet."
        if (
            search_text
            or status_filter != "all"
            or priority_filter != "all"
            or schedule_filter != "all"
        ):
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
    def _coerce_string_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple)):
            result: list[str] = []
            for item in value:
                normalized = str(item or "").strip()
                if normalized:
                    result.append(normalized)
            return result
        normalized = str(value or "").strip()
        return [normalized] if normalized else []

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

    @classmethod
    def _require_date(cls, payload: dict[str, Any], key: str, message: str) -> date:
        value = cls._optional_date(payload, key)
        if value is None:
            raise ValueError(message)
        return value

    @staticmethod
    def _optional_iso_date(value: str) -> date | None:
        normalized_value = str(value or "").strip()
        if not normalized_value:
            return None
        try:
            return date.fromisoformat(normalized_value)
        except ValueError as exc:
            raise ValueError("Dates must use YYYY-MM-DD.") from exc

    def preview_assignment(self, payload: dict[str, Any]) -> dict[str, object]:
        task_id = str(payload.get("taskId") or "").strip()
        project_resource_id = str(payload.get("projectResourceId") or "").strip()
        if not task_id or not project_resource_id:
            return {
                "ok": True,
                "overallocationPct": 0.0,
                "conflictProjects": [],
                "skillsMatched": True,
                "certsValid": True,
                "hasWarnings": False,
                "warningMessages": [],
                "isBlocked": False,
                "blockMessages": [],
            }
        from src.core.modules.project_management.api.desktop.tasks import (
            AssignmentPreviewDesktopDto,
        )
        dto: AssignmentPreviewDesktopDto = self._desktop_api.preview_assignment(
            task_id, project_resource_id
        )
        return {
            "ok": True,
            "overallocationPct": dto.overallocation_pct,
            "conflictProjects": list(dto.conflict_projects),
            "skillsMatched": dto.skills_matched,
            "certsValid": dto.certs_valid,
            "hasWarnings": dto.has_warnings,
            "warningMessages": list(dto.warning_messages),
            "isBlocked": dto.is_blocked,
            "blockMessages": list(dto.block_messages),
        }

    def validate_assignment(self, payload: dict[str, Any]) -> dict[str, object]:
        task_id = str(payload.get("taskId") or "").strip()
        project_resource_id = str(payload.get("projectResourceId") or "").strip()
        if not task_id or not project_resource_id:
            return {
                "ok": True,
                "isValid": True,
                "canAssign": True,
                "requiresApproval": False,
                "isBlocked": False,
                "hasWarnings": False,
                "violationMessages": [],
                "warningMessages": [],
                "summary": "valid",
            }
        dto: AssignmentValidationDesktopDto = self._desktop_api.validate_assignment(
            task_id, project_resource_id
        )
        return {
            "ok": True,
            "isValid": dto.is_valid,
            "canAssign": dto.can_assign,
            "requiresApproval": dto.requires_approval,
            "isBlocked": dto.is_blocked,
            "hasWarnings": dto.has_warnings,
            "violationMessages": list(dto.violation_messages),
            "warningMessages": list(dto.warning_messages),
            "summary": dto.summary,
        }


__all__ = ["ProjectTasksWorkspacePresenter"]
