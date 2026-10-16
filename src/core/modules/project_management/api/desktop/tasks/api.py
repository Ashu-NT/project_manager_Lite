from __future__ import annotations

import logging
from typing import TypeVar

from src.core.modules.project_management.api.desktop.common.constraint_presentation import (
    EDITABLE_CONSTRAINT_OPTIONS,
)
from src.core.modules.project_management.api.desktop.common.dependency_presentation import (
    coerce_dependency_direction,
    coerce_dependency_type,
    dependency_type_label,
)
from src.core.modules.project_management.api.desktop.tasks.builders.project_options_builder import (
    build_project_options,
)
from src.core.modules.project_management.api.desktop.tasks.builders.resource_options_builder import (
    build_project_resource_options,
)
from src.core.modules.project_management.api.desktop.tasks.builders.status_options_builder import (
    build_status_options,
)
from src.core.modules.project_management.api.desktop.tasks.models.options import (
    TaskConstraintOptionDescriptor,
    TaskDependencyTypeDescriptor,
    TaskProjectOptionDescriptor,
    TaskProjectResourceOptionDescriptor,
    TaskStatusDescriptor,
)
from src.core.modules.project_management.api.desktop.tasks.services.access_resolution_service import (
    project_rows_for_task_scope,
)
from src.core.modules.project_management.api.desktop.tasks.utils.task_id_utils import (
    normalize_task_ids,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
from src.core.modules.project_management.application.resources import (
    ProjectResourceQueryHandler,
    ResourceQueryHandler,
)
from src.core.modules.project_management.application.resources.catalog.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.scheduling.dto.responses.change_impact import (
    DownstreamExposureDto,
    ScheduleImpactReportDto,
)
from src.core.modules.project_management.application.scheduling.dto.responses.overview import (
    TaskScheduleOverviewResponseDto,
)
from src.core.modules.project_management.application.scheduling.forecasting.queries.change_impact import (
    ScheduleChangeImpactQueryHandler,
)
from src.core.modules.project_management.application.tasks import (
    TaskDeletionCommandHandler,
    TaskDependencyCommandHandler,
    TaskDependencyQueryHandler,
    TaskHierarchyCommandHandler,
    TaskHierarchyQueryHandler,
    TaskLifecycleCommandHandler,
    TaskLookupQueryHandler,
    TaskProgressCommandHandler,
    TaskSchedulingConstraintHandler,
)
from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.time_entries import (
    TaskTimeEntryHandler,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_assignments import (
    TaskAssignmentAllocationCommand,
    TaskAssignmentCreateCommand,
    TaskAssignmentHoursCommand,
    TaskAssignmentPlannedHoursCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_constraints import (
    TaskConstraintUpdateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_dependencies import (
    TaskDependencyCreateCommand,
    TaskDependencyUpdateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_hierarchy import (
    TaskWbsMoveCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_lifecycle import (
    TaskCreateCommand,
    TaskUpdateCommand,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_progress import (
    TaskBulkStatusCommand,
    TaskProgressCommand,
)
from src.core.modules.project_management.application.tasks.dto.responses.assignment_validation import (
    AssignmentPreviewResponseDto, AssignmentValidationResponseDto,
)
from src.core.modules.project_management.application.tasks.queries.assignment_preview import query_assignment_preview
from src.core.modules.project_management.application.tasks.queries.assignment_validation import query_assignment_validation
from src.core.modules.project_management.application.tasks.dto.responses.assignment import (
    TaskAssignmentResponseDto,
)
from src.core.modules.project_management.application.tasks.dto.responses.dependency import (
    TaskDependencyResponseDto,
)
from src.core.modules.project_management.application.tasks.dto.responses.skill_requirement import TaskSkillRequirementResponseDto
from src.core.modules.project_management.application.tasks.queries.skill_requirements import query_skill_requirements
from src.core.modules.project_management.application.tasks.dto.responses.task import (
    TaskResponseDto,
)
from src.core.modules.project_management.application.tasks.queries.dependency_diagnostics import (
    DependencyDiagnostic,
    TaskDependencyDiagnosticsQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_detail_page import (
    TaskDetailPageQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_workspace_page import (
    TaskWorkspacePageQueryHandler,
)
from src.core.modules.project_management.contracts.reads.tasks import (
    TaskActivityPage,
    TaskAssignmentReadPage,
    TaskDependencyReadItem,
    TaskDependencyReadPage,
    TaskWorkspaceReadPage,
)
from src.core.modules.project_management.contracts.reads.tasks.models import (
    TaskTimeEntriesPage,
    TaskTimeSummaryFact,
)
from src.core.modules.project_management.domain.enums import DependencyType
from src.core.modules.project_management.gateway.task.reservation import (
    TaskReservationGateway,
)
from src.core.platform.application.tenant.modules.authorization import (
    require_module_enabled,
)
from src.core.platform.common.exceptions import ConfigurationError
from src.core.platform.contract.port.tenant.modules.supports_module_entitlements import (
    SupportsModuleEntitlements,
)

logger = logging.getLogger(__name__)

_CapabilityT = TypeVar("_CapabilityT")


class ProjectManagementTasksDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectQueryHandler | None = None,
        task_lookup_query: TaskLookupQueryHandler | None = None,
        task_hierarchy_query: TaskHierarchyQueryHandler | None = None,
        task_deletion_commands: TaskDeletionCommandHandler | None = None,
        task_progress_commands: TaskProgressCommandHandler | None = None,
        task_hierarchy_commands: TaskHierarchyCommandHandler | None = None,
        task_constraint_commands: TaskSchedulingConstraintHandler | None = None,
        task_lifecycle_commands: TaskLifecycleCommandHandler | None = None,
        task_dependency_commands: TaskDependencyCommandHandler | None = None,
        task_dependency_query: TaskDependencyQueryHandler | None = None,
        task_workspace_query: TaskWorkspacePageQueryHandler | None = None,
        task_detail_query: TaskDetailPageQueryHandler | None = None,
        task_dependency_diagnostics: TaskDependencyDiagnosticsQueryHandler | None = None,
        task_assignment_commands: TaskAssignmentCommandHandler | None = None,
        task_time_entries: TaskTimeEntryHandler | None = None,
        module_catalog_service: SupportsModuleEntitlements | None = None,
        project_resource_query: ProjectResourceQueryHandler | None = None,
        resource_query: ResourceQueryHandler | None = None,
        reservation_service: TaskReservationGateway | None = None,
        assignment_skill_validator: AssignmentSkillValidator | None = None,
        schedule_change_impact_query: ScheduleChangeImpactQueryHandler | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_lookup_query = task_lookup_query
        self._task_hierarchy_query = task_hierarchy_query
        self._task_deletion_commands = task_deletion_commands
        self._task_progress_commands = task_progress_commands
        self._task_hierarchy_commands = task_hierarchy_commands
        self._task_constraint_commands = task_constraint_commands
        self._task_lifecycle_commands = task_lifecycle_commands
        self._task_dependency_commands = task_dependency_commands
        self._task_dependency_query = task_dependency_query
        self._task_workspace_query = task_workspace_query
        self._task_detail_query = task_detail_query
        self._task_dependency_diagnostics = task_dependency_diagnostics
        self._task_assignment_commands = task_assignment_commands
        self._task_time_entries = task_time_entries
        self._module_catalog_service = module_catalog_service
        self._project_resource_query = project_resource_query
        self._resource_service = resource_query
        self._reservation_service = reservation_service
        self._assignment_skill_validator = assignment_skill_validator
        self._schedule_change_impact_query = schedule_change_impact_query

    def list_projects(self) -> tuple[TaskProjectOptionDescriptor, ...]:
        return build_project_options(
            project_service=self._project_service,
        )

    def list_statuses(self) -> tuple[TaskStatusDescriptor, ...]:
        return build_status_options()

    def list_project_resources(
        self,
        project_id: str,
    ) -> tuple[TaskProjectResourceOptionDescriptor, ...]:
        return build_project_resource_options(
            project_id,
            project_resource_query=self._project_resource_query,
            resource_query=self._resource_service,
        )

    def get_task(self, task_id: str) -> TaskResponseDto | None:
        if not task_id:
            return None
        task = self._require_task_capability(self._task_detail_query).get_task(task_id)
        if task is None:
            return None
        rows = self._project_tasks(task.project_id)
        return next((row for row in rows if row.id == task.id), None)

    def _project_tasks(self, project_id: str) -> tuple[TaskResponseDto, ...]:
        return self._require_task_capability(self._task_hierarchy_query).query_task_responses(project_id)

    def list_dependency_types(self) -> tuple[TaskDependencyTypeDescriptor, ...]:
        return tuple(
            TaskDependencyTypeDescriptor(
                value=dependency_type.value,
                label=dependency_type_label(dependency_type),
            )
            for dependency_type in DependencyType
        )

    def list_tasks(self, project_id: str) -> tuple[TaskResponseDto, ...]:
        return self._project_tasks(project_id)

    def list_task_page(
        self,
        *,
        project_id: str | None = None,
        search_text: str = "",
        status: str = "all",
        priority: str = "all",
        schedule: str = "all",
        milestones_only: bool = False,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "wbsCode",
        sort_direction: str = "asc",
    ) -> TaskWorkspaceReadPage:
        if self._task_workspace_query is None:
            raise ConfigurationError("Project management tasks desktop API is not connected.")
        require_module_enabled(
            self._module_catalog_service,
            "project_management",
            operation_label="query workspace page",
        )
        result = self._task_workspace_query.query_workspace_page(
            project_id=project_id,
            search_text=search_text,
            status=status,
            priority=priority,
            schedule=schedule,
            milestones_only=milestones_only,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return result

    def create_task(self, command: TaskCreateCommand) -> TaskResponseDto:
        return self._require_task_capability(self._task_lifecycle_commands).create_task(command)

    def list_constraint_options(self) -> tuple[TaskConstraintOptionDescriptor, ...]:
        return tuple(
            TaskConstraintOptionDescriptor(
                value=option.value.value if option.value is not None else "",
                code=option.code,
                label=option.label,
                description=option.description,
                requires_date=option.requires_date,
                category=option.category,
            )
            for option in EDITABLE_CONSTRAINT_OPTIONS
        )

    def update_task_scheduling_constraint(
        self, command: TaskConstraintUpdateCommand
    ) -> TaskResponseDto:
        return self._require_task_capability(self._task_constraint_commands).update_task_scheduling_constraint(command)

    def move_task(self, command: TaskWbsMoveCommand) -> TaskResponseDto:
        task = self._require_task_capability(self._task_hierarchy_commands).move_task(command)
        refreshed = self.get_task(task.id)
        if refreshed is None:
            raise RuntimeError("Task could not be loaded after the WBS move.")
        return refreshed

    def update_task(self, command: TaskUpdateCommand) -> TaskResponseDto:
        return self._require_task_capability(self._task_lifecycle_commands).update_task(command)

    def update_progress(self, command: TaskProgressCommand) -> TaskResponseDto:
        return self._require_task_capability(self._task_progress_commands).update_progress(command)

    def list_assignments(self, task_id: str) -> tuple[TaskAssignmentResponseDto, ...]:
        if not task_id or self._task_assignment_commands is None:
            return ()
        return self._task_assignment_commands.query_assignment_responses(task_id)

    def list_assignments_page(
        self, task_id: str, *, search_text: str = "", response_status: str = "all",
        page: int = 1, page_size: int = 25, sort_key: str = "resourceName",
        sort_direction: str = "asc",
    ) -> TaskAssignmentReadPage:
        result = self._require_task_detail_query().query_task_assignments_page(
            task_id, search_text=search_text, response_status=response_status,
            page=page, page_size=page_size, sort_key=sort_key, sort_direction=sort_direction)
        return result

    def get_task_time_summary(self, task_id: str) -> TaskTimeSummaryFact | None:
        """Task-scoped planned/actual/remaining/overrun totals plus the
        per-resource breakdown for Task Detail -> Time -> Overview.
        None when the task can't be resolved."""
        if not task_id:
            return None
        fact = self._require_task_assignment_commands().get_task_time_summary(task_id)
        if fact is None:
            return None
        return fact

    def list_task_time_entries(
        self,
        task_id: str,
        *,
        resource_id: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_direction: str = "desc",
    ) -> TaskTimeEntriesPage | None:
        """Task-scoped (every assignment on this task), all-time Time
        Entries listing for Task Detail -> Time -> Time Entries.
        None when the task can't be resolved."""
        if not task_id:
            return None
        return self._require_task_time_entries().list_time_entries_for_task_page(
            task_id,
            resource_id=resource_id or None,
            page=page,
            page_size=page_size,
            sort_direction=sort_direction,
        )

    def create_assignment(
        self,
        command: TaskAssignmentCreateCommand,
    ) -> TaskAssignmentResponseDto:
        return self._require_task_capability(self._task_assignment_commands).assign_project_resource(command)

    def update_assignment_allocation(
        self,
        command: TaskAssignmentAllocationCommand,
    ) -> TaskAssignmentResponseDto:
        return self._require_task_capability(self._task_assignment_commands).set_assignment_allocation(command)

    def update_assignment_planned_hours(
        self,
        command: TaskAssignmentPlannedHoursCommand,
    ) -> TaskAssignmentResponseDto:
        return self._require_task_capability(self._task_assignment_commands).update_assignment_planned_hours(command)

    def set_assignment_hours(
        self,
        command: TaskAssignmentHoursCommand,
    ) -> TaskAssignmentResponseDto:
        return self._require_task_assignment_commands(
            operation_label="log assignment hours"
        ).set_assignment_hours(command)

    def delete_assignment(self, assignment_id: str) -> None:
        self._require_task_capability(self._task_assignment_commands).unassign_resource(assignment_id)

    def accept_assignment(self, assignment_id: str) -> TaskAssignmentResponseDto:
        return self._require_task_capability(self._task_assignment_commands).accept_assignment(assignment_id)

    def decline_assignment(self, assignment_id: str, reason: str = "") -> TaskAssignmentResponseDto:
        return self._require_task_capability(self._task_assignment_commands).decline_assignment(assignment_id, reason or None)

    def list_dependencies(self, task_id: str) -> tuple[TaskDependencyReadItem, ...]:
        if not task_id or self._task_dependency_query is None or self._task_detail_query is None or self._task_lookup_query is None:
            return ()
        if self._task_detail_query.get_task(task_id) is None:
            return ()
        return self._task_dependency_query.query_dependency_responses(task_id)

    def list_dependencies_page(
        self, task_id: str, *, search_text: str = "", direction: str = "all",
        dependency_type: str = "all", page: int = 1, page_size: int = 25,
        sort_key: str = "linkedTask", sort_direction: str = "asc",
    ) -> TaskDependencyReadPage:
        result = self._require_task_detail_query().query_task_dependencies_page(
            task_id, search_text=search_text, direction=direction,
            dependency_type=dependency_type, page=page, page_size=page_size,
            sort_key=sort_key, sort_direction=sort_direction)
        return result

    def list_task_activity_page(
        self, task_id: str, *, search_text: str = "", category: str = "all",
        page: int = 1, page_size: int = 25,
    ) -> TaskActivityPage:
        result = self._require_task_detail_query().query_task_activity_page(
            task_id, search_text=search_text, category=category, page=page, page_size=page_size)
        return result

    def create_dependency(self, command: TaskDependencyCreateCommand) -> TaskDependencyResponseDto:
        return self._require_task_capability(self._task_dependency_commands).add_dependency(command)

    def update_dependency(
        self,
        command: TaskDependencyUpdateCommand,
    ) -> None:
        normalized_id = (command.dependency_id or "").strip()
        if not normalized_id:
            raise ValueError("Dependency ID is required.")
        self._require_task_capability(self._task_dependency_commands).update_dependency(command)

    def delete_dependency(self, dependency_id: str) -> None:
        self._require_task_capability(self._task_dependency_commands).remove_dependency(dependency_id)

    def preview_create_dependency(
        self,
        command: TaskDependencyCreateCommand,
    ) -> DependencyDiagnostic | None:
        """Non-persisting impact preview for a proposed CREATE. Uses the
        same canonical, non-persisting engine the committed schedule uses
        -- never a second formula, never QML-side math."""
        diagnostics = self._require_dependency_diagnostics()
        relationship_direction = coerce_dependency_direction(command.relationship_direction)
        predecessor_id = (
            command.linked_task_id if relationship_direction == "PREDECESSOR" else command.task_id
        )
        successor_id = (
            command.task_id if relationship_direction == "PREDECESSOR" else command.linked_task_id
        )
        diagnostic = diagnostics.get_dependency_diagnostics(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=coerce_dependency_type(command.dependency_type),
            lag_days=command.lag_days,
            include_impact=True,
        )
        return diagnostic

    def preview_update_dependency(
        self,
        command: TaskDependencyUpdateCommand,
    ) -> DependencyDiagnostic | None:
        """Non-persisting impact preview for a proposed UPDATE."""
        diagnostics = self._require_dependency_diagnostics()
        get_dependency = getattr(self._task_dependency_query, "get_dependency", None)
        if not callable(get_dependency):
            return None
        normalized_id = (command.dependency_id or "").strip()
        if not normalized_id:
            return None
        existing = get_dependency(normalized_id)
        if existing is None:
            return None
        diagnostic = diagnostics.get_dependency_diagnostics(
            predecessor_id=existing.predecessor_task_id,
            successor_id=existing.successor_task_id,
            dependency_type=coerce_dependency_type(command.dependency_type),
            lag_days=command.lag_days,
            include_impact=True,
            exclude_dependency_id=normalized_id,
        )
        return diagnostic

    def preview_delete_dependency(
        self, dependency_id: str
    ) -> DependencyDiagnostic | None:
        """Non-persisting impact preview for a proposed DELETE."""
        diagnostic = self._require_dependency_diagnostics().preview_dependency_removal(
            dependency_id
        )
        return diagnostic

    def delete_task(self, task_id: str) -> None:
        self._require_task_capability(self._task_deletion_commands).delete_task(task_id)

    def apply_bulk_status(
        self,
        command: TaskBulkStatusCommand,
    ) -> tuple[TaskResponseDto, ...]:
        changed = self._require_task_capability(self._task_progress_commands).set_tasks_status(command)
        return tuple(changed)

    def delete_tasks(self, task_ids: tuple[str, ...]) -> tuple[str, ...]:
        normalized_ids = normalize_task_ids(task_ids)
        return tuple(self._require_task_capability(self._task_deletion_commands).delete_tasks(normalized_ids))

    def list_task_skill_requirements(
        self,
        task_id: str,
    ) -> tuple[TaskSkillRequirementResponseDto, ...]:
        if not task_id or self._assignment_skill_validator is None:
            return ()
        try:
            return query_skill_requirements(self._assignment_skill_validator, task_id)
        except Exception:
            logger.exception(
                "list_task_skill_requirements failed (task_id=%s)",
                task_id,
            )
            return ()

    def validate_assignment(
        self,
        task_id: str,
        project_resource_id: str,
    ) -> AssignmentValidationResponseDto:
        return query_assignment_validation(
            task_id,
            project_resource_id,
            task_query=self._task_detail_query,
            project_resource_query=self._project_resource_query,
            assignment_skill_validator=self._assignment_skill_validator,
        )

    def preview_assignment(
        self,
        task_id: str,
        project_resource_id: str,
        *,
        proposed_allocation_percent: float = 100.0,
        exclude_assignment_id: str | None = None,
    ) -> AssignmentPreviewResponseDto:
        return query_assignment_preview(
            task_id,
            project_resource_id,
            task_query=self._task_detail_query,
            assignment_commands=self._task_assignment_commands,
            project_resource_query=self._project_resource_query,
            assignment_skill_validator=self._assignment_skill_validator,
            proposed_allocation_percent=proposed_allocation_percent,
            exclude_assignment_id=exclude_assignment_id,
        )

    def get_task_schedule_overview(
        self,
        task_id: str,
        project_id: str,
    ) -> TaskScheduleOverviewResponseDto:
        """Task Detail -> Schedule Impact's always-visible current-state
        facts (position, criticality, float, drivers, conflicts,
        downstream exposure) -- no hypothetical simulation, safe to load
        automatically on task selection."""
        normalized_task_id = str(task_id or "").strip()
        normalized_project_id = str(project_id or "").strip()
        if not normalized_task_id or not normalized_project_id:
            return self._unavailable_schedule_overview(
                normalized_task_id, unavailable_reason="missing_task_or_project_id"
            )
        if self._schedule_change_impact_query is None:
            logger.warning(
                "Schedule impact requested but no ScheduleChangeImpactQueryHandler is wired "
                "(task_id=%s, project_id=%s) -- check the Scheduling query capability "
                "in module-owned composition.",
                normalized_task_id,
                normalized_project_id,
            )
            return self._unavailable_schedule_overview(
                normalized_task_id, unavailable_reason="service_not_configured"
            )
        try:
            overview = self._schedule_change_impact_query.get_task_schedule_overview(
                normalized_project_id, normalized_task_id
            )
        except Exception:
            logger.exception(
                "get_task_schedule_overview failed (task_id=%s, project_id=%s)",
                normalized_task_id,
                normalized_project_id,
            )
            return self._unavailable_schedule_overview(
                normalized_task_id, unavailable_reason="error"
            )
        logger.debug(
            "get_task_schedule_overview result task_id=%s project_id=%s is_available=%s unavailable_reason=%s",
            normalized_task_id,
            normalized_project_id,
            overview.is_available,
            overview.unavailable_reason,
        )
        return overview

    @staticmethod
    def _unavailable_schedule_overview(
        task_id: str, *, unavailable_reason: str
    ) -> TaskScheduleOverviewResponseDto:
        return TaskScheduleOverviewResponseDto(
            task_id=task_id, is_available=False, unavailable_reason=unavailable_reason,
            current_start=None, current_finish=None, is_critical=False, is_infeasible=False,
            total_float_days=None, free_float_days=None, baseline_finish=None,
            schedule_variance_days=None, drivers=(), dependency_conflicts=(),
            actual_variances=(), downstream=DownstreamExposureDto(0, 0, 0, 0),
        )

    def preview_task_schedule_impact(
        self,
        task_id: str,
        project_id: str,
        *,
        delay_working_days: int = 1,
    ) -> ScheduleImpactReportDto:
        """Task Detail -> Schedule Impact's explicit "Preview Impact"
        what-if -- a non-persisting simulation, run only when the user
        asks for it, never automatically on task selection."""
        normalized_task_id = str(task_id or "").strip()
        normalized_project_id = str(project_id or "").strip()
        unavailable = ScheduleImpactReportDto(
            task_id=normalized_task_id,
            project_id=normalized_project_id,
            simulated_delay_days=delay_working_days,
            is_available=False,
            affected_count=0,
            max_project_finish_shift_days=0,
            requires_approval=False,
            affected_tasks=(),
            newly_critical_task_ids=(),
            no_longer_critical_task_ids=(),
        )
        if (
            not normalized_task_id
            or not normalized_project_id
            or self._task_detail_query is None
            or self._schedule_change_impact_query is None
        ):
            return unavailable
        try:
            task = self._require_task_capability(self._task_detail_query).get_task(normalized_task_id)
            if task is None or task.start_date is None:
                logger.debug(
                    "preview_task_schedule_impact unavailable: task=%s start_date=%s",
                    normalized_task_id,
                    task.start_date if task is not None else None,
                )
                return unavailable
            report = self._schedule_change_impact_query.analyse_working_day_delay(
                project_id=normalized_project_id,
                changed_task_id=normalized_task_id,
                current_start=task.start_date,
                delay_working_days=delay_working_days,
            )
        except Exception:
            logger.exception(
                "preview_task_schedule_impact failed (task_id=%s, project_id=%s, delay_working_days=%s)",
                normalized_task_id,
                normalized_project_id,
                delay_working_days,
            )
            return unavailable
        return report


    def _require_task_capability(self, capability: _CapabilityT | None) -> _CapabilityT:
        if capability is None:
            raise ConfigurationError('Project management tasks desktop API is not connected.')
        return capability

    def _require_task_detail_query(self) -> TaskDetailPageQueryHandler:
        if self._task_detail_query is None:
            raise ConfigurationError("Project management tasks desktop API is not connected.")
        require_module_enabled(
            self._module_catalog_service,
            "project_management",
            operation_label="query task detail page",
        )
        return self._task_detail_query

    def _require_dependency_diagnostics(self) -> TaskDependencyDiagnosticsQueryHandler:
        if self._task_dependency_diagnostics is None:
            raise ConfigurationError("Project management tasks desktop API is not connected.")
        require_module_enabled(
            self._module_catalog_service,
            "project_management",
            operation_label="preview task dependency",
        )
        return self._task_dependency_diagnostics

    def _require_task_assignment_commands(
        self, *, operation_label: str = "view task time summary"
    ) -> TaskAssignmentCommandHandler:
        if self._task_assignment_commands is None:
            raise ConfigurationError("Project management tasks desktop API is not connected.")
        require_module_enabled(
            self._module_catalog_service,
            "project_management",
            operation_label=operation_label,
        )
        return self._task_assignment_commands

    def _require_task_time_entries(self) -> TaskTimeEntryHandler:
        if self._task_time_entries is None:
            raise ConfigurationError("Project management tasks desktop API is not connected.")
        require_module_enabled(
            self._module_catalog_service,
            "project_management",
            operation_label="view task time entries",
        )
        return self._task_time_entries


    def _project_name_by_id(self) -> dict[str, str]:
        return {
            project.id: project.name
            for project in project_rows_for_task_scope(
                project_service=self._project_service,
            )
        }


__all__ = ["ProjectManagementTasksDesktopApi"]
