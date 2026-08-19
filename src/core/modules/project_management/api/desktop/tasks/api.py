from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from src.core.modules.project_management.api.desktop.scheduling.models.change_impact import (
    ScheduleImpactReportDto,
    TaskScheduleImpactOverviewDesktopDto,
)
from src.core.modules.project_management.api.desktop.scheduling.serializers.change_impact_serializer import (
    serialize_schedule_impact_report,
    serialize_task_schedule_overview,
)
from src.core.modules.project_management.api.desktop.tasks.builders.assignment_preview_builder import (
    build_assignment_preview,
)
from src.core.modules.project_management.api.desktop.tasks.builders.assignment_validation_builder import (
    build_assignment_validation,
)
from src.core.modules.project_management.api.desktop.tasks.builders.material_demand_builder import (
    build_material_demand_summary,
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
from src.core.modules.project_management.api.desktop.tasks.serializers.time_summary_serializer import (
    serialize_task_time_entries_page,
    serialize_task_time_summary,
)
from src.core.modules.project_management.api.desktop.tasks.serializers.dependency_impact_preview_serializer import (
    serialize_dependency_impact_preview,
)
from src.core.modules.project_management.api.desktop.tasks.models.dependency import (
    TaskDependencyImpactPreviewDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.models.time_summary import (
    TaskTimeEntriesPageDesktopDto,
    TaskTimeSummaryDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.commands.assignment_commands import (
    TaskAssignmentAllocationCommand,
    TaskAssignmentCreateCommand,
    TaskAssignmentHoursCommand,
    TaskAssignmentPlannedHoursCommand,
)
from src.core.modules.project_management.api.desktop.tasks.commands.bulk_commands import (
    TaskBulkStatusCommand,
)
from src.core.modules.project_management.api.desktop.tasks.commands.dependency_commands import (
    TaskDependencyCreateCommand,
    TaskDependencyUpdateCommand,
)
from src.core.modules.project_management.api.desktop.tasks.commands.reservation_commands import (
    TaskReservationCreateCommand,
)
from src.core.modules.project_management.api.desktop.tasks.commands.task_commands import (
    TaskCreateCommand,
    TaskProgressCommand,
    TaskUpdateCommand,
    TaskWbsMoveCommand,
)
from src.core.modules.project_management.api.desktop.tasks.models.assignment import (
    TaskAssignmentDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.models.dependency import (
    TaskDependencyDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.models.options import (
    TaskDependencyTypeDescriptor,
    TaskProjectOptionDescriptor,
    TaskProjectResourceOptionDescriptor,
    TaskStatusDescriptor,
)
from src.core.modules.project_management.api.desktop.tasks.models.reservation import (
    TaskMaterialDemandSummary,
    TaskReservationDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.models.skill import (
    TaskSkillRequirementDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.models.task import (
    TaskDesktopDto,
    TaskWorkspacePageDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.models.validation import (
    AssignmentPreviewDesktopDto,
    AssignmentValidationDesktopDto,
)
from src.core.modules.project_management.api.desktop.tasks.serializers.assignment_serializer import (
    serialize_assignment,
)
from src.core.modules.project_management.api.desktop.tasks.serializers.dependency_serializer import (
    serialize_dependency,
)
from src.core.modules.project_management.api.desktop.tasks.serializers.reservation_serializer import (
    serialize_reservation,
)
from src.core.modules.project_management.api.desktop.tasks.serializers.skill_serializer import (
    serialize_skill_requirement,
)
from src.core.modules.project_management.api.desktop.tasks.serializers.task_serializer import (
    serialize_task,
)
from src.core.modules.project_management.api.desktop.tasks.services.access_resolution_service import (
    project_rows_for_task_scope,
)
from src.core.modules.project_management.api.desktop.tasks.services.resource_lookup_service import (
    resource_by_id,
    resource_name_for_assignment,
)
from src.core.modules.project_management.api.desktop.common.dependency_presentation import (
    coerce_dependency_direction,
    coerce_dependency_type,
    dependency_direction,
    dependency_type_label,
)
from src.core.modules.project_management.api.desktop.tasks.utils.task_id_utils import (
    normalize_task_ids,
)
from src.core.modules.project_management.api.desktop.tasks.utils.task_status_utils import (
    coerce_task_status,
)
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    ProjectResourceService,
    ResourceService,
)
from src.core.modules.project_management.application.resources.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.scheduling.forecasting.schedule_change_impact_service import (
    ScheduleChangeImpactService,
)
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.domain.enums import DependencyType, TaskStatus
from src.core.modules.project_management.gateway.task.reservation import (
    TaskReservationGateway,
)
from src.core.platform.common.exceptions import BusinessRuleError


logger = logging.getLogger(__name__)


class ProjectManagementTasksDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        task_service: TaskService | None = None,
        project_resource_service: ProjectResourceService | None = None,
        resource_service: ResourceService | None = None,
        reservation_service: TaskReservationGateway | None = None,
        assignment_skill_validator: AssignmentSkillValidator | None = None,
        schedule_change_impact_service: ScheduleChangeImpactService | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._project_resource_service = project_resource_service
        self._resource_service = resource_service
        self._reservation_service = reservation_service
        self._assignment_skill_validator = assignment_skill_validator
        self._schedule_change_impact_service = schedule_change_impact_service

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
            project_resource_service=self._project_resource_service,
            resource_service=self._resource_service,
        )

    def get_task(self, task_id: str) -> TaskDesktopDto | None:
        if not task_id:
            return None
        service = self._require_task_service()
        task = service.get_task(task_id)
        if task is None:
            return None
        rows = self._serialize_project_tasks(
            task.project_id,
            self._project_name_by_id().get(task.project_id, ""),
        )
        return next((row for row in rows if row.id == task.id), None)

    def _serialize_project_tasks(
        self,
        project_id: str,
        project_name: str,
    ) -> tuple[TaskDesktopDto, ...]:
        service = self._require_task_service()
        list_hierarchy = getattr(service, "list_task_hierarchy", None)
        list_rollups = getattr(service, "list_task_hierarchy_rollups", None)
        if callable(list_hierarchy) and callable(list_rollups):
            nodes = list_hierarchy(project_id)
            rollups = list_rollups(project_id)
            return tuple(
                serialize_task(
                    node.task,
                    project_name=project_name,
                    hierarchy_node=node,
                    rollup=rollups.get(node.task.id),
                )
                for node in nodes
            )
        tasks = sorted(
            service.list_tasks_for_project(project_id),
            key=lambda task: (
                task.start_date or date.max,
                -int(task.priority or 0),
                (task.name or "").casefold(),
            ),
        )
        return tuple(serialize_task(task, project_name=project_name) for task in tasks)

    def list_dependency_types(self) -> tuple[TaskDependencyTypeDescriptor, ...]:
        return tuple(
            TaskDependencyTypeDescriptor(
                value=dependency_type.value,
                label=dependency_type_label(dependency_type),
            )
            for dependency_type in DependencyType
        )

    def list_tasks(self, project_id: str) -> tuple[TaskDesktopDto, ...]:
        project_name = self._project_name_by_id().get(project_id, "")
        return self._serialize_project_tasks(project_id, project_name)

    def list_task_page(
        self,
        *,
        project_id: str | None = None,
        search_text: str = "",
        status: str = "all",
        priority: str = "all",
        schedule: str = "all",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "wbsCode",
        sort_direction: str = "asc",
    ) -> TaskWorkspacePageDesktopDto:
        service = self._require_task_service()
        result = service.query_workspace_page(
            project_id=project_id,
            search_text=search_text,
            status=status,
            priority=priority,
            schedule=schedule,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return TaskWorkspacePageDesktopDto(
            items=tuple(
                TaskDesktopDto(
                    id=item.id,
                    project_id=item.project_id,
                    project_name=item.project_name,
                    name=item.name,
                    code=item.code,
                    description=item.description,
                    status=item.status,
                    status_label=item.status.replace("_", " ").title(),
                    start_date=item.start_date,
                    end_date=item.end_date,
                    duration_days=item.duration_days,
                    priority=item.priority,
                    percent_complete=item.percent_complete,
                    actual_start=item.actual_start,
                    actual_end=item.actual_end,
                    deadline=item.deadline,
                    version=item.version,
                    parent_task_id=item.parent_task_id,
                    wbs_code=item.wbs_code,
                    sort_order=item.sort_order,
                    is_summary=item.is_summary,
                    hierarchy_depth=item.hierarchy_depth,
                    child_count=item.child_count,
                )
                for item in result.items
            ),
            filtered_total=result.filtered_total,
            total=result.summary.total,
            in_progress=result.summary.in_progress,
            blocked=result.summary.blocked,
            done=result.summary.done,
            overdue=result.summary.overdue,
            page=result.page,
            page_size=result.page_size,
            sort_key=result.sort.key,
            sort_direction=result.sort.direction.value,
        )

    def create_task(self, command: TaskCreateCommand) -> TaskDesktopDto:
        service = self._require_task_service()
        task = service.create_task(
            project_id=command.project_id,
            name=command.name,
            code=getattr(command, "code", ""),
            description=command.description,
            start_date=command.start_date,
            duration_days=command.duration_days,
            priority=command.priority or 0,
            deadline=command.deadline,
            parent_task_id=getattr(command, "parent_task_id", None),
            wbs_code=getattr(command, "wbs_code", "") or "",
            sort_order=getattr(command, "sort_order", None),
        )
        desired_status = coerce_task_status(command.status)
        if desired_status != task.status:
            service.set_status(task.id, desired_status)
            task = service.get_task(task.id) or task
        return serialize_task(
            task,
            project_name=self._project_name_by_id().get(task.project_id, ""),
        )

    def move_task(self, command: TaskWbsMoveCommand) -> TaskDesktopDto:
        task = self._require_task_service().move_task(
            command.task_id,
            parent_task_id=command.parent_task_id,
            wbs_code=command.wbs_code,
            sort_order=command.sort_order,
            expected_version=command.expected_version,
        )
        refreshed = self.get_task(task.id)
        if refreshed is None:
            raise RuntimeError("Task could not be loaded after the WBS move.")
        return refreshed

    def update_task(self, command: TaskUpdateCommand) -> TaskDesktopDto:
        service = self._require_task_service()
        current_task = service.get_task(command.task_id)
        if current_task is None:
            raise RuntimeError("Task could not be loaded for update.")
        desired_status = coerce_task_status(command.status)
        task = service.update_task(
            command.task_id,
            name=command.name,
            code=getattr(command, "code", ""),
            description=command.description,
            start_date=command.start_date,
            duration_days=command.duration_days,
            status=current_task.status,
            priority=command.priority,
            deadline=command.deadline,
            expected_version=command.expected_version,
        )
        if desired_status != current_task.status:
            service.set_status(task.id, desired_status)
            task = service.get_task(task.id) or task
        return serialize_task(
            task,
            project_name=self._project_name_by_id().get(task.project_id, ""),
        )

    def update_progress(self, command: TaskProgressCommand) -> TaskDesktopDto:
        task = self._require_task_service().update_progress(
            command.task_id,
            percent_complete=command.percent_complete,
            actual_start=command.actual_start,
            actual_end=command.actual_end,
            status=(
                coerce_task_status(command.status)
                if command.status is not None
                else None
            ),
            expected_version=command.expected_version,
        )
        return serialize_task(
            task,
            project_name=self._project_name_by_id().get(task.project_id, ""),
        )

    def _project_resource_version_for(self, assignment) -> int:
        project_resource_id = str(getattr(assignment, "project_resource_id", "") or "")
        if not project_resource_id or self._project_resource_service is None:
            return 1
        try:
            project_resource = self._project_resource_service.get(project_resource_id)
        except Exception:
            return 1
        return int(getattr(project_resource, "version", 1) or 1)

    def list_assignments(self, task_id: str) -> tuple[TaskAssignmentDesktopDto, ...]:
        if not task_id:
            return ()
        service = self._require_task_service()
        list_assignments_for_task = getattr(service, "list_assignments_for_task", None)
        if not callable(list_assignments_for_task):
            return ()
        assignments = list(list_assignments_for_task(task_id))
        resources_by_id = resource_by_id(
            resource_service=self._resource_service,
            resource_ids=tuple(
                str(getattr(assignment, "resource_id", "") or "")
                for assignment in assignments
            ),
        )
        assignments = sorted(
            assignments,
            key=lambda assignment: (
                resource_name_for_assignment(
                    assignment,
                    resources_by_id=resources_by_id,
                ).casefold(),
                -float(getattr(assignment, "allocation_percent", 0.0) or 0.0),
            ),
        )
        action_context_method = getattr(service, "get_assignment_action_context", None)
        preview_capacity_method = getattr(service, "preview_assignment_capacity", None)
        rows: list[TaskAssignmentDesktopDto] = []
        for assignment in assignments:
            action_context = None
            if callable(action_context_method):
                try:
                    action_context = action_context_method(assignment.id)
                except Exception:
                    logger.warning(
                        "Assignment capabilities could not be resolved assignment_id=%s",
                        assignment.id,
                        exc_info=True,
                    )
                    action_context = None
            capacity_fact = None
            if callable(preview_capacity_method):
                try:
                    # This assignment's own allocation_percent stands in as
                    # "proposed" against every OTHER assignment already
                    # committed (exclude_assignment_id) -- i.e. the real
                    # capacity fact for this assignment's current commitment,
                    # from the same authority the create/edit preview uses
                    # (docs §44), not a second calculation.
                    capacity_fact = preview_capacity_method(
                        task_id,
                        assignment.resource_id,
                        proposed_allocation_percent=float(
                            getattr(assignment, "allocation_percent", 0.0) or 0.0
                        ),
                        exclude_assignment_id=assignment.id,
                    )
                except Exception:
                    logger.warning(
                        "Assignment capacity could not be resolved assignment_id=%s",
                        assignment.id,
                        exc_info=True,
                    )
                    capacity_fact = None
            rows.append(
                serialize_assignment(
                    assignment,
                    resources_by_id=resources_by_id,
                    can_manage=bool(getattr(action_context, "can_manage", False)),
                    can_accept=bool(getattr(action_context, "can_accept", False)),
                    can_decline=bool(getattr(action_context, "can_decline", False)),
                    project_resource_version=self._project_resource_version_for(assignment),
                    capacity_fact=capacity_fact,
                )
            )
        return tuple(rows)

    def get_task_time_summary(self, task_id: str) -> TaskTimeSummaryDesktopDto | None:
        """Task-scoped planned/actual/remaining/overrun totals plus the
        per-resource breakdown for Task Detail -> Time -> Overview (docs
        §44 Time redesign). None when the task can't be resolved."""
        if not task_id:
            return None
        service = self._require_task_service()
        get_summary = getattr(service, "get_task_time_summary", None)
        if not callable(get_summary):
            return None
        fact = get_summary(task_id)
        return serialize_task_time_summary(fact)

    def list_task_time_entries(
        self,
        task_id: str,
        *,
        resource_id: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_direction: str = "desc",
    ) -> TaskTimeEntriesPageDesktopDto | None:
        """Task-scoped (every assignment on this task), all-time Time
        Entries listing for Task Detail -> Time -> Time Entries (docs §44
        Time redesign). None when the task can't be resolved."""
        if not task_id:
            return None
        service = self._require_task_service()
        list_page = getattr(service, "list_time_entries_for_task_page", None)
        if not callable(list_page):
            return None
        page_result = list_page(
            task_id,
            resource_id=resource_id or None,
            page=page,
            page_size=page_size,
            sort_direction=sort_direction,
        )
        resources_by_id = resource_by_id(
            resource_service=self._resource_service,
            resource_ids=tuple({row.resource_id for row in page_result.items}),
        )
        return serialize_task_time_entries_page(page_result, resources_by_id=resources_by_id)

    def create_assignment(
        self,
        command: TaskAssignmentCreateCommand,
    ) -> TaskAssignmentDesktopDto:
        assignment = self._require_task_method("assign_project_resource")(
            task_id=command.task_id,
            project_resource_id=command.project_resource_id,
            allocation_percent=command.allocation_percent,
            allocated_planned_hours=getattr(command, "allocated_planned_hours", None) or Decimal("0"),
        )
        return serialize_assignment(
            assignment,
            resources_by_id=resource_by_id(
                resource_service=self._resource_service,
                resource_ids=(str(getattr(assignment, "resource_id", "") or ""),),
            ),
            project_resource_version=self._project_resource_version_for(assignment),
        )

    def update_assignment_allocation(
        self,
        command: TaskAssignmentAllocationCommand,
    ) -> TaskAssignmentDesktopDto:
        assignment = self._require_task_method("set_assignment_allocation")(
            assignment_id=command.assignment_id,
            allocation_percent=command.allocation_percent,
            expected_version=getattr(command, "expected_version", None),
        )
        return serialize_assignment(
            assignment,
            resources_by_id=resource_by_id(
                resource_service=self._resource_service,
                resource_ids=(str(getattr(assignment, "resource_id", "") or ""),),
            ),
            project_resource_version=self._project_resource_version_for(assignment),
        )

    def update_assignment_planned_hours(
        self,
        command: TaskAssignmentPlannedHoursCommand,
    ) -> TaskAssignmentDesktopDto:
        assignment = self._require_task_method("update_assignment_planned_hours")(
            assignment_id=command.assignment_id,
            allocated_planned_hours=command.allocated_planned_hours,
            expected_assignment_version=command.expected_assignment_version,
            expected_project_resource_version=command.expected_project_resource_version,
        )
        return serialize_assignment(
            assignment,
            resources_by_id=resource_by_id(
                resource_service=self._resource_service,
                resource_ids=(str(getattr(assignment, "resource_id", "") or ""),),
            ),
            project_resource_version=self._project_resource_version_for(assignment),
        )

    def set_assignment_hours(
        self,
        command: TaskAssignmentHoursCommand,
    ) -> TaskAssignmentDesktopDto:
        assignment = self._require_task_method("set_assignment_hours")(
            assignment_id=command.assignment_id,
            hours_logged=command.hours_logged,
        )
        return serialize_assignment(
            assignment,
            resources_by_id=resource_by_id(
                resource_service=self._resource_service,
                resource_ids=(str(getattr(assignment, "resource_id", "") or ""),),
            ),
            project_resource_version=self._project_resource_version_for(assignment),
        )

    def delete_assignment(self, assignment_id: str) -> None:
        self._require_task_method("unassign_resource")(assignment_id)

    def accept_assignment(self, assignment_id: str) -> TaskAssignmentDesktopDto:
        assignment = self._require_task_method("accept_assignment")(assignment_id)
        return serialize_assignment(
            assignment,
            resources_by_id=resource_by_id(
                resource_service=self._resource_service,
                resource_ids=(str(getattr(assignment, "resource_id", "") or ""),),
            ),
            project_resource_version=self._project_resource_version_for(assignment),
        )

    def decline_assignment(self, assignment_id: str, reason: str = "") -> TaskAssignmentDesktopDto:
        assignment = self._require_task_method("decline_assignment")(assignment_id, reason or None)
        return serialize_assignment(
            assignment,
            resources_by_id=resource_by_id(
                resource_service=self._resource_service,
                resource_ids=(str(getattr(assignment, "resource_id", "") or ""),),
            ),
            project_resource_version=self._project_resource_version_for(assignment),
        )

    def list_dependencies(self, task_id: str) -> tuple[TaskDependencyDesktopDto, ...]:
        if not task_id:
            return ()
        service = self._require_task_service()
        list_dependencies_for_task = getattr(service, "list_dependencies_for_task", None)
        get_task = getattr(service, "get_task", None)
        list_tasks_for_project = getattr(service, "list_tasks_for_project", None)
        if (
            not callable(list_dependencies_for_task)
            or not callable(get_task)
            or not callable(list_tasks_for_project)
        ):
            return ()
        current_task = get_task(task_id)
        if current_task is None:
            return ()
        tasks_by_id = {
            task.id: task
            for task in list_tasks_for_project(current_task.project_id)
        }
        rows = [
            serialize_dependency(
                dependency,
                current_task_id=current_task.id,
                tasks_by_id=tasks_by_id,
            )
            for dependency in list_dependencies_for_task(task_id)
            if dependency_direction(current_task.id, dependency)[0]
        ]
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    row.direction != "PREDECESSOR",
                    row.linked_task_name.casefold(),
                ),
            )
        )

    def create_dependency(
        self,
        command: TaskDependencyCreateCommand,
    ) -> TaskDependencyDesktopDto:
        relationship_direction = coerce_dependency_direction(
            command.relationship_direction
        )
        predecessor_id = (
            command.linked_task_id
            if relationship_direction == "PREDECESSOR"
            else command.task_id
        )
        successor_id = (
            command.task_id
            if relationship_direction == "PREDECESSOR"
            else command.linked_task_id
        )
        dependency = self._require_task_method("add_dependency")(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=coerce_dependency_type(command.dependency_type),
            lag_days=command.lag_days,
        )
        current_task = self._require_task_method("get_task")(command.task_id)
        tasks_by_id: dict[str, object] = {}
        list_tasks_for_project = getattr(self._task_service, "list_tasks_for_project", None)
        if current_task is not None and callable(list_tasks_for_project):
            tasks_by_id = {
                task.id: task
                for task in list_tasks_for_project(current_task.project_id)
            }
        return serialize_dependency(
            dependency,
            current_task_id=command.task_id,
            tasks_by_id=tasks_by_id,
        )

    def update_dependency(
        self,
        command: TaskDependencyUpdateCommand,
    ) -> None:
        normalized_id = (command.dependency_id or "").strip()
        if not normalized_id:
            raise ValueError("Dependency ID is required.")
        self._require_task_method("update_dependency")(
            normalized_id,
            dependency_type=coerce_dependency_type(command.dependency_type),
            lag_days=command.lag_days,
            expected_version=command.expected_version,
        )

    def delete_dependency(self, dependency_id: str) -> None:
        self._require_task_method("remove_dependency")(dependency_id)

    def preview_create_dependency(
        self,
        command: TaskDependencyCreateCommand,
    ) -> TaskDependencyImpactPreviewDesktopDto | None:
        """Non-persisting impact preview for a proposed CREATE (Phase K).
        Uses the same canonical, non-persisting engine the committed
        schedule uses -- never a second formula, never QML-side math."""
        service = self._require_task_service()
        get_diagnostics = getattr(service, "get_dependency_diagnostics", None)
        if not callable(get_diagnostics):
            return None
        relationship_direction = coerce_dependency_direction(command.relationship_direction)
        predecessor_id = (
            command.linked_task_id if relationship_direction == "PREDECESSOR" else command.task_id
        )
        successor_id = (
            command.task_id if relationship_direction == "PREDECESSOR" else command.linked_task_id
        )
        diagnostic = get_diagnostics(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=coerce_dependency_type(command.dependency_type),
            lag_days=command.lag_days,
            include_impact=True,
        )
        return serialize_dependency_impact_preview(diagnostic)

    def preview_update_dependency(
        self,
        command: TaskDependencyUpdateCommand,
    ) -> TaskDependencyImpactPreviewDesktopDto | None:
        """Non-persisting impact preview for a proposed UPDATE (Phase K)."""
        service = self._require_task_service()
        get_diagnostics = getattr(service, "get_dependency_diagnostics", None)
        get_dependency = getattr(service, "get_dependency", None)
        if not callable(get_diagnostics) or not callable(get_dependency):
            return None
        normalized_id = (command.dependency_id or "").strip()
        if not normalized_id:
            return None
        existing = get_dependency(normalized_id)
        if existing is None:
            return None
        diagnostic = get_diagnostics(
            predecessor_id=existing.predecessor_task_id,
            successor_id=existing.successor_task_id,
            dependency_type=coerce_dependency_type(command.dependency_type),
            lag_days=command.lag_days,
            include_impact=True,
            exclude_dependency_id=normalized_id,
        )
        return serialize_dependency_impact_preview(diagnostic)

    def preview_delete_dependency(
        self, dependency_id: str
    ) -> TaskDependencyImpactPreviewDesktopDto | None:
        """Non-persisting impact preview for a proposed DELETE (Phase K)."""
        service = self._require_task_service()
        preview = getattr(service, "preview_dependency_removal", None)
        if not callable(preview):
            return None
        diagnostic = preview(dependency_id)
        return serialize_dependency_impact_preview(diagnostic)

    def delete_task(self, task_id: str) -> None:
        self._require_task_service().delete_task(task_id)

    def apply_bulk_status(
        self,
        command: TaskBulkStatusCommand,
    ) -> tuple[TaskDesktopDto, ...]:
        service = self._require_task_service()
        desired_status = coerce_task_status(command.status)
        task_ids = normalize_task_ids(command.task_ids)
        changed = service.set_tasks_status(
            task_ids,
            desired_status,
            reopen_percent_complete=command.reopen_percent_complete,
        )
        project_names = self._project_name_by_id()
        return tuple(
            serialize_task(
                task,
                project_name=project_names.get(task.project_id, ""),
            )
            for task in changed
        )

    def delete_tasks(self, task_ids: tuple[str, ...]) -> tuple[str, ...]:
        normalized_ids = normalize_task_ids(task_ids)
        service = self._require_task_service()
        return tuple(service.delete_tasks(normalized_ids))

    def list_task_reservations(self, task_id: str) -> tuple[TaskReservationDesktopDto, ...]:
        if not task_id or self._reservation_service is None:
            return ()
        all_reservations = self._reservation_service.list_reservations(limit=500)
        task_reservations = [
            reservation for reservation in all_reservations
            if getattr(reservation, "source_reference_type", "") == "task"
            and getattr(reservation, "source_reference_id", "") == task_id
        ]
        return tuple(
            serialize_reservation(reservation)
            for reservation in sorted(
                task_reservations,
                key=lambda reservation: getattr(reservation, "created_at", None) or "",
            )
        )

    def create_task_reservation(
        self,
        command: TaskReservationCreateCommand,
    ) -> TaskReservationDesktopDto:
        if self._reservation_service is None:
            raise RuntimeError("Inventory reservation service is not connected.")
        task = self._require_task_service().get_task(command.task_id)
        if task is None:
            raise RuntimeError("Task not found.")
        reservation = self._reservation_service.create_reservation(
            stock_item_id=command.stock_item_id,
            storeroom_id=command.storeroom_id,
            reserved_qty=command.reserved_qty,
            uom=command.uom,
            need_by_date=command.need_by_date,
            source_reference_type="task",
            source_reference_id=command.task_id,
            source_module="project_management",
            source_entity_type="task",
            source_code_snapshot=str(getattr(task, "name", "") or ""),
            source_status_snapshot=str(
                getattr(getattr(task, "status", None), "value", "") or ""
            ),
            notes=command.notes,
        )
        return serialize_reservation(reservation)

    def get_task_material_demand(self, task_id: str) -> TaskMaterialDemandSummary:
        return build_material_demand_summary(
            task_id,
            self.list_task_reservations(task_id),
        )

    def list_task_skill_requirements(
        self,
        task_id: str,
    ) -> tuple[TaskSkillRequirementDesktopDto, ...]:
        if not task_id or self._assignment_skill_validator is None:
            return ()
        try:
            requirements = self._assignment_skill_validator.list_requirements(task_id)
        except Exception:
            return ()
        return tuple(serialize_skill_requirement(req) for req in requirements)

    def validate_assignment(
        self,
        task_id: str,
        project_resource_id: str,
    ) -> AssignmentValidationDesktopDto:
        return build_assignment_validation(
            task_id,
            project_resource_id,
            task_service=self._task_service,
            project_resource_service=self._project_resource_service,
            assignment_skill_validator=self._assignment_skill_validator,
        )

    def preview_assignment(
        self,
        task_id: str,
        project_resource_id: str,
        *,
        proposed_allocation_percent: float = 100.0,
        exclude_assignment_id: str | None = None,
    ) -> AssignmentPreviewDesktopDto:
        return build_assignment_preview(
            task_id,
            project_resource_id,
            task_service=self._task_service,
            project_resource_service=self._project_resource_service,
            assignment_skill_validator=self._assignment_skill_validator,
            proposed_allocation_percent=proposed_allocation_percent,
            exclude_assignment_id=exclude_assignment_id,
            project_names=self._project_name_by_id(),
        )

    def get_task_schedule_overview(
        self,
        task_id: str,
        project_id: str,
    ) -> TaskScheduleImpactOverviewDesktopDto:
        """Task Detail -> Schedule Impact's always-visible current-state
        facts (position, criticality, float, drivers, conflicts,
        downstream exposure) -- no hypothetical simulation, safe to load
        automatically on task selection (§26)."""
        normalized_task_id = str(task_id or "").strip()
        normalized_project_id = str(project_id or "").strip()
        if (
            not normalized_task_id
            or not normalized_project_id
            or self._schedule_change_impact_service is None
        ):
            return serialize_task_schedule_overview(normalized_task_id)
        try:
            overview = self._schedule_change_impact_service.get_task_schedule_overview(
                normalized_project_id, normalized_task_id
            )
        except Exception:
            return serialize_task_schedule_overview(normalized_task_id)
        return serialize_task_schedule_overview(normalized_task_id, overview)

    def preview_task_schedule_impact(
        self,
        task_id: str,
        project_id: str,
        *,
        delay_working_days: int = 1,
    ) -> ScheduleImpactReportDto:
        """Task Detail -> Schedule Impact's explicit "Preview Impact"
        what-if (§12/§13) -- a non-persisting simulation, run only when
        the user asks for it, never automatically on task selection."""
        normalized_task_id = str(task_id or "").strip()
        normalized_project_id = str(project_id or "").strip()
        unavailable = serialize_schedule_impact_report(
            task_id=normalized_task_id,
            project_id=normalized_project_id,
            simulated_delay_days=delay_working_days,
        )
        if (
            not normalized_task_id
            or not normalized_project_id
            or self._task_service is None
            or self._schedule_change_impact_service is None
        ):
            return unavailable
        try:
            task = self._task_service.get_task(normalized_task_id)
            if task is None or task.start_date is None:
                return unavailable
            report = self._schedule_change_impact_service.analyse_working_day_delay(
                project_id=normalized_project_id,
                changed_task_id=normalized_task_id,
                current_start=task.start_date,
                delay_working_days=delay_working_days,
            )
        except Exception:
            return unavailable
        return serialize_schedule_impact_report(
            task_id=normalized_task_id,
            project_id=normalized_project_id,
            simulated_delay_days=delay_working_days,
            report=report,
        )

    def _require_task_service(self) -> TaskService:
        if self._task_service is None:
            raise RuntimeError("Project management tasks desktop API is not connected.")
        return self._task_service

    def _require_task_method(self, method_name: str):
        service = self._require_task_service()
        method = getattr(service, method_name, None)
        if not callable(method):
            raise RuntimeError(
                f"Project management tasks desktop API does not support {method_name}."
            )
        return method

    def _project_name_by_id(self) -> dict[str, str]:
        return {
            project.id: project.name
            for project in project_rows_for_task_scope(
                project_service=self._project_service,
            )
        }


__all__ = ["ProjectManagementTasksDesktopApi"]
