from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.scheduling.builders.change_impact_builder import (
    compute_schedule_impact,
)
from src.core.modules.project_management.api.desktop.scheduling.models.change_impact import (
    ScheduleImpactReportDto,
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
from src.core.modules.project_management.api.desktop.tasks.commands.assignment_commands import (
    TaskAssignmentAllocationCommand,
    TaskAssignmentCreateCommand,
    TaskAssignmentHoursCommand,
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
from src.core.modules.project_management.api.desktop.tasks.models.task import TaskDesktopDto
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
from src.core.modules.project_management.api.desktop.tasks.utils.dependency_utils import (
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
from src.core.modules.project_management.application.resources.resource_availability_service import (
    ResourceAvailabilityService,
)
from src.core.modules.project_management.application.scheduling.forecasting.schedule_change_impact_service import (
    ScheduleChangeImpactService,
)
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.domain.enums import DependencyType, TaskStatus
from src.core.platform.common.exceptions import BusinessRuleError


class ProjectManagementTasksDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        task_service: TaskService | None = None,
        project_resource_service: ProjectResourceService | None = None,
        resource_service: ResourceService | None = None,
        reservation_service: object | None = None,
        assignment_skill_validator: AssignmentSkillValidator | None = None,
        schedule_change_impact_service: ScheduleChangeImpactService | None = None,
        resource_availability_service: ResourceAvailabilityService | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._project_resource_service = project_resource_service
        self._resource_service = resource_service
        self._reservation_service = reservation_service
        self._assignment_skill_validator = assignment_skill_validator
        self._schedule_change_impact_service = schedule_change_impact_service
        self._resource_availability_service = resource_availability_service

    def list_projects(self) -> tuple[TaskProjectOptionDescriptor, ...]:
        return build_project_options(
            project_service=self._project_service,
            task_service=self._task_service,
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
            task_service=self._task_service,
        )

    def get_task(self, task_id: str) -> TaskDesktopDto | None:
        if not task_id:
            return None
        service = self._require_task_service()
        task = service.get_task(task_id)
        if task is None:
            return None
        return serialize_task(
            task,
            project_name=self._project_name_by_id().get(task.project_id, ""),
        )

    def list_dependency_types(self) -> tuple[TaskDependencyTypeDescriptor, ...]:
        return tuple(
            TaskDependencyTypeDescriptor(
                value=dependency_type.value,
                label=dependency_type_label(dependency_type),
            )
            for dependency_type in DependencyType
        )

    def list_tasks(self, project_id: str) -> tuple[TaskDesktopDto, ...]:
        service = self._require_task_service()
        project_name = self._project_name_by_id().get(project_id, "")
        tasks = sorted(
            service.list_tasks_for_project(project_id),
            key=lambda task: (
                task.start_date or date.max,
                -int(task.priority or 0),
                (task.name or "").casefold(),
            ),
        )
        return tuple(serialize_task(task, project_name=project_name) for task in tasks)

    def list_all_tasks(self) -> tuple[TaskDesktopDto, ...]:
        service = self._require_task_service()
        project_name_lookup = self._project_name_by_id()
        if not project_name_lookup:
            return ()
        all_tasks: list[TaskDesktopDto] = []
        for project_id, project_name in project_name_lookup.items():
            try:
                tasks = service.list_tasks_for_project(project_id)
            except BusinessRuleError:
                continue
            all_tasks.extend(
                serialize_task(task, project_name=project_name)
                for task in tasks
            )
        return tuple(
            sorted(
                all_tasks,
                key=lambda task: (
                    task.start_date or date.max,
                    -int(task.priority or 0),
                    (task.name or "").casefold(),
                ),
            )
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
        )
        desired_status = coerce_task_status(command.status)
        if desired_status != task.status:
            service.set_status(task.id, desired_status)
            task = service.get_task(task.id) or task
        return serialize_task(
            task,
            project_name=self._project_name_by_id().get(task.project_id, ""),
        )

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
            task_service=self._task_service,
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
        return tuple(
            serialize_assignment(assignment, resources_by_id=resources_by_id)
            for assignment in assignments
        )

    def create_assignment(
        self,
        command: TaskAssignmentCreateCommand,
    ) -> TaskAssignmentDesktopDto:
        assignment = self._require_task_method("assign_project_resource")(
            task_id=command.task_id,
            project_resource_id=command.project_resource_id,
            allocation_percent=command.allocation_percent,
        )
        return serialize_assignment(
            assignment,
            resources_by_id=resource_by_id(
                resource_service=self._resource_service,
                task_service=self._task_service,
                resource_ids=(str(getattr(assignment, "resource_id", "") or ""),),
            ),
        )

    def update_assignment_allocation(
        self,
        command: TaskAssignmentAllocationCommand,
    ) -> TaskAssignmentDesktopDto:
        assignment = self._require_task_method("set_assignment_allocation")(
            assignment_id=command.assignment_id,
            allocation_percent=command.allocation_percent,
        )
        return serialize_assignment(
            assignment,
            resources_by_id=resource_by_id(
                resource_service=self._resource_service,
                task_service=self._task_service,
                resource_ids=(str(getattr(assignment, "resource_id", "") or ""),),
            ),
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
                task_service=self._task_service,
                resource_ids=(str(getattr(assignment, "resource_id", "") or ""),),
            ),
        )

    def delete_assignment(self, assignment_id: str) -> None:
        self._require_task_method("unassign_resource")(assignment_id)

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
        )

    def delete_dependency(self, dependency_id: str) -> None:
        self._require_task_method("remove_dependency")(dependency_id)

    def delete_task(self, task_id: str) -> None:
        self._require_task_service().delete_task(task_id)

    def apply_bulk_status(
        self,
        command: TaskBulkStatusCommand,
    ) -> tuple[TaskDesktopDto, ...]:
        service = self._require_task_service()
        desired_status = coerce_task_status(command.status)
        task_ids = normalize_task_ids(command.task_ids)
        changed_tasks: list[TaskDesktopDto] = []
        for task_id in task_ids:
            task = service.get_task(task_id)
            if task is None or task.status == desired_status:
                continue
            if (
                task.status == TaskStatus.DONE
                and desired_status == TaskStatus.IN_PROGRESS
                and command.reopen_percent_complete is not None
            ):
                task = service.update_progress(
                    task_id,
                    status=TaskStatus.IN_PROGRESS,
                    percent_complete=float(command.reopen_percent_complete),
                )
            else:
                service.set_status(task_id, desired_status)
                task = service.get_task(task_id) or task
            changed_tasks.append(
                serialize_task(
                    task,
                    project_name=self._project_name_by_id().get(task.project_id, ""),
                )
            )
        return tuple(changed_tasks)

    def delete_tasks(self, task_ids: tuple[str, ...]) -> tuple[str, ...]:
        normalized_ids = normalize_task_ids(task_ids)
        deleted_ids: list[str] = []
        for task_id in normalized_ids:
            task = self._require_task_service().get_task(task_id)
            if task is None:
                continue
            self._require_task_service().delete_task(task_id)
            deleted_ids.append(task_id)
        return tuple(deleted_ids)

    def list_task_reservations(self, task_id: str) -> tuple[TaskReservationDesktopDto, ...]:
        if not task_id or self._reservation_service is None:
            return ()
        list_reservations = getattr(self._reservation_service, "list_reservations", None)
        if not callable(list_reservations):
            return ()
        try:
            all_reservations = list_reservations(limit=500)
        except Exception:
            return ()
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
        create_reservation = getattr(self._reservation_service, "create_reservation", None)
        if not callable(create_reservation):
            raise RuntimeError(
                "Inventory reservation service does not support create_reservation."
            )
        task = self._require_task_service().get_task(command.task_id)
        if task is None:
            raise RuntimeError("Task not found.")
        reservation = create_reservation(
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
    ) -> AssignmentPreviewDesktopDto:
        return build_assignment_preview(
            task_id,
            project_resource_id,
            task_service=self._task_service,
            project_resource_service=self._project_resource_service,
            assignment_skill_validator=self._assignment_skill_validator,
            resource_availability_service=self._resource_availability_service,
        )

    def get_schedule_impact(
        self,
        task_id: str,
        project_id: str,
    ) -> ScheduleImpactReportDto:
        return compute_schedule_impact(
            task_id,
            project_id,
            task_service=self._task_service,
            schedule_change_impact_service=self._schedule_change_impact_service,
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
                task_service=self._task_service,
            )
        }


__all__ = ["ProjectManagementTasksDesktopApi"]
