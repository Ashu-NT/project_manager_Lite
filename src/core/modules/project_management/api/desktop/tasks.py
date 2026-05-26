from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    ProjectResourceService,
    ResourceService,
)
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.domain.enums import DependencyType, TaskStatus


@dataclass(frozen=True)
class TaskProjectOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class TaskStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class TaskProjectResourceOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class TaskDependencyTypeDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class TaskDesktopDto:
    id: str
    project_id: str
    project_name: str
    name: str
    description: str
    status: str
    status_label: str
    start_date: date | None
    end_date: date | None
    duration_days: int | None
    priority: int | None
    percent_complete: float
    actual_start: date | None
    actual_end: date | None
    deadline: date | None
    version: int


@dataclass(frozen=True)
class TaskCreateCommand:
    project_id: str
    name: str
    description: str = ""
    start_date: date | None = None
    duration_days: int | None = None
    status: str = TaskStatus.TODO.value
    priority: int | None = None
    deadline: date | None = None


@dataclass(frozen=True)
class TaskUpdateCommand:
    task_id: str
    name: str
    description: str = ""
    start_date: date | None = None
    duration_days: int | None = None
    status: str = TaskStatus.TODO.value
    priority: int | None = None
    deadline: date | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class TaskProgressCommand:
    task_id: str
    percent_complete: float | None = None
    actual_start: date | None = None
    actual_end: date | None = None
    status: str | None = None
    expected_version: int | None = None


@dataclass(frozen=True)
class TaskAssignmentDesktopDto:
    id: str
    task_id: str
    resource_id: str
    resource_name: str
    allocation_percent: float
    hours_logged: float
    project_resource_id: str | None


@dataclass(frozen=True)
class TaskAssignmentCreateCommand:
    task_id: str
    project_resource_id: str
    allocation_percent: float = 100.0


@dataclass(frozen=True)
class TaskAssignmentAllocationCommand:
    assignment_id: str
    allocation_percent: float


@dataclass(frozen=True)
class TaskAssignmentHoursCommand:
    assignment_id: str
    hours_logged: float


@dataclass(frozen=True)
class TaskDependencyDesktopDto:
    id: str
    direction: str
    direction_label: str
    linked_task_id: str
    linked_task_name: str
    dependency_type: str
    dependency_type_label: str
    lag_days: int
    relationship_label: str


@dataclass(frozen=True)
class TaskDependencyCreateCommand:
    task_id: str
    linked_task_id: str
    relationship_direction: str
    dependency_type: str = DependencyType.FINISH_TO_START.value
    lag_days: int = 0


@dataclass(frozen=True)
class TaskBulkStatusCommand:
    task_ids: tuple[str, ...]
    status: str
    reopen_percent_complete: float | None = None


@dataclass(frozen=True)
class TaskReservationDesktopDto:
    id: str
    reservation_number: str
    stock_item_id: str
    storeroom_id: str
    reserved_qty: float
    issued_qty: float
    remaining_qty: float
    uom: str
    status: str
    status_label: str
    need_by_date: date | None
    notes: str


@dataclass(frozen=True)
class TaskReservationCreateCommand:
    task_id: str
    stock_item_id: str
    storeroom_id: str
    reserved_qty: float
    uom: str | None = None
    need_by_date: date | None = None
    notes: str = ""


@dataclass(frozen=True)
class TaskMaterialDemandSummary:
    task_id: str
    total_reserved: int
    active_count: int
    fulfilled_count: int
    cancelled_count: int


class ProjectManagementTasksDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        task_service: TaskService | None = None,
        project_resource_service: ProjectResourceService | None = None,
        resource_service: ResourceService | None = None,
        reservation_service: object | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._project_resource_service = project_resource_service
        self._resource_service = resource_service
        self._reservation_service = reservation_service

    def list_projects(self) -> tuple[TaskProjectOptionDescriptor, ...]:
        if self._project_service is None:
            return ()
        projects = sorted(
            self._project_service.list_projects(),
            key=lambda project: (project.name or "").casefold(),
        )
        return tuple(
            TaskProjectOptionDescriptor(value=project.id, label=project.name)
            for project in projects
        )

    def list_statuses(self) -> tuple[TaskStatusDescriptor, ...]:
        return tuple(
            TaskStatusDescriptor(
                value=status.value,
                label=status.value.replace("_", " ").title(),
            )
            for status in TaskStatus
        )

    def list_project_resources(
        self,
        project_id: str,
    ) -> tuple[TaskProjectResourceOptionDescriptor, ...]:
        if (
            not project_id
            or self._project_resource_service is None
            or self._resource_service is None
        ):
            return ()
        list_by_project = getattr(self._project_resource_service, "list_by_project", None)
        list_resources = getattr(self._resource_service, "list_resources", None)
        if not callable(list_by_project) or not callable(list_resources):
            return ()
        resources_by_id = {
            resource.id: resource
            for resource in list_resources()
        }
        options: list[TaskProjectResourceOptionDescriptor] = []
        for project_resource in list_by_project(project_id):
            resource = resources_by_id.get(project_resource.resource_id)
            if resource is None:
                continue
            if not getattr(project_resource, "is_active", True) or not getattr(
                resource,
                "is_active",
                True,
            ):
                continue
            rate = (
                getattr(project_resource, "hourly_rate", None)
                if getattr(project_resource, "hourly_rate", None) is not None
                else getattr(resource, "hourly_rate", None)
            )
            currency = (
                getattr(project_resource, "currency_code", None)
                or getattr(resource, "currency_code", None)
                or ""
            ).upper()
            label = str(getattr(resource, "name", "") or project_resource.resource_id)
            if rate is not None:
                rate_label = f"{float(rate):.2f}"
                if currency:
                    label += f" ({rate_label} {currency}/hr)"
                else:
                    label += f" ({rate_label}/hr)"
            options.append(
                TaskProjectResourceOptionDescriptor(
                    value=project_resource.id,
                    label=label,
                )
            )
        return tuple(
            sorted(options, key=lambda option: option.label.casefold())
        )

    def list_dependency_types(self) -> tuple[TaskDependencyTypeDescriptor, ...]:
        return tuple(
            TaskDependencyTypeDescriptor(
                value=dependency_type.value,
                label=_dependency_type_label(dependency_type),
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
        return tuple(
            self._serialize_task(task, project_name=project_name)
            for task in tasks
        )

    def list_all_tasks(self) -> tuple[TaskDesktopDto, ...]:
        if self._project_service is None:
            return ()
        project_name_lookup = self._project_name_by_id()
        service = self._require_task_service()
        all_tasks: list[TaskDesktopDto] = []
        for project_id, project_name in project_name_lookup.items():
            all_tasks.extend(
                self._serialize_task(task, project_name=project_name)
                for task in service.list_tasks_for_project(project_id)
            )
        return tuple(
            sorted(
                all_tasks,
                key=lambda t: (
                    t.start_date or date.max,
                    -int(t.priority or 0),
                    (t.name or "").casefold(),
                ),
            )
        )

    def create_task(self, command: TaskCreateCommand) -> TaskDesktopDto:
        service = self._require_task_service()
        task = service.create_task(
            project_id=command.project_id,
            name=command.name,
            description=command.description,
            start_date=command.start_date,
            duration_days=command.duration_days,
            priority=command.priority or 0,
            deadline=command.deadline,
        )
        desired_status = _coerce_task_status(command.status)
        if desired_status != task.status:
            service.set_status(task.id, desired_status)
            task = service.get_task(task.id) or task
        return self._serialize_task(
            task,
            project_name=self._project_name_by_id().get(task.project_id, ""),
        )

    def update_task(self, command: TaskUpdateCommand) -> TaskDesktopDto:
        service = self._require_task_service()
        current_task = service.get_task(command.task_id)
        if current_task is None:
            raise RuntimeError("Task could not be loaded for update.")
        desired_status = _coerce_task_status(command.status)
        task = service.update_task(
            command.task_id,
            name=command.name,
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
        return self._serialize_task(
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
                _coerce_task_status(command.status)
                if command.status is not None
                else None
            ),
            expected_version=command.expected_version,
        )
        return self._serialize_task(
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
        resources_by_id = self._resource_by_id()
        assignments = sorted(
            list_assignments_for_task(task_id),
            key=lambda assignment: (
                self._resource_name_for_assignment(
                    assignment,
                    resources_by_id=resources_by_id,
                ).casefold(),
                -float(getattr(assignment, "allocation_percent", 0.0) or 0.0),
            ),
        )
        return tuple(
            self._serialize_assignment(
                assignment,
                resources_by_id=resources_by_id,
            )
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
        return self._serialize_assignment(
            assignment,
            resources_by_id=self._resource_by_id(),
        )

    def update_assignment_allocation(
        self,
        command: TaskAssignmentAllocationCommand,
    ) -> TaskAssignmentDesktopDto:
        assignment = self._require_task_method("set_assignment_allocation")(
            assignment_id=command.assignment_id,
            allocation_percent=command.allocation_percent,
        )
        return self._serialize_assignment(
            assignment,
            resources_by_id=self._resource_by_id(),
        )

    def set_assignment_hours(
        self,
        command: TaskAssignmentHoursCommand,
    ) -> TaskAssignmentDesktopDto:
        assignment = self._require_task_method("set_assignment_hours")(
            assignment_id=command.assignment_id,
            hours_logged=command.hours_logged,
        )
        return self._serialize_assignment(
            assignment,
            resources_by_id=self._resource_by_id(),
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
            self._serialize_dependency(
                dependency,
                current_task_id=current_task.id,
                tasks_by_id=tasks_by_id,
            )
            for dependency in list_dependencies_for_task(task_id)
            if _dependency_direction(current_task.id, dependency)[0]
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
        relationship_direction = _coerce_dependency_direction(
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
            dependency_type=_coerce_dependency_type(command.dependency_type),
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
        return self._serialize_dependency(
            dependency,
            current_task_id=command.task_id,
            tasks_by_id=tasks_by_id,
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
        desired_status = _coerce_task_status(command.status)
        task_ids = _normalize_task_ids(command.task_ids)
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
                updated = service.update_progress(
                    task_id,
                    status=TaskStatus.IN_PROGRESS,
                    percent_complete=float(command.reopen_percent_complete),
                )
                task = updated
            else:
                service.set_status(task_id, desired_status)
                task = service.get_task(task_id) or task
            changed_tasks.append(
                self._serialize_task(
                    task,
                    project_name=self._project_name_by_id().get(task.project_id, ""),
                )
            )
        return tuple(changed_tasks)

    def delete_tasks(self, task_ids: tuple[str, ...]) -> tuple[str, ...]:
        normalized_ids = _normalize_task_ids(task_ids)
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
            r for r in all_reservations
            if getattr(r, "source_reference_type", "") == "task"
            and getattr(r, "source_reference_id", "") == task_id
        ]
        return tuple(
            self._serialize_reservation(r)
            for r in sorted(
                task_reservations,
                key=lambda r: getattr(r, "created_at", None) or "",
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
            raise RuntimeError("Inventory reservation service does not support create_reservation.")
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
        return self._serialize_reservation(reservation)

    def get_task_material_demand(self, task_id: str) -> TaskMaterialDemandSummary:
        reservations = self.list_task_reservations(task_id)
        active_statuses = {"ACTIVE", "PARTIALLY_ISSUED"}
        fulfilled_statuses = {"FULLY_ISSUED"}
        closed_statuses = {"RELEASED", "CANCELLED"}
        return TaskMaterialDemandSummary(
            task_id=task_id,
            total_reserved=len(reservations),
            active_count=sum(1 for r in reservations if r.status in active_statuses),
            fulfilled_count=sum(1 for r in reservations if r.status in fulfilled_statuses),
            cancelled_count=sum(1 for r in reservations if r.status in closed_statuses),
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
        if self._project_service is None:
            return {}
        return {
            project.id: project.name
            for project in self._project_service.list_projects()
        }

    def _resource_by_id(self) -> dict[str, object]:
        if self._resource_service is None:
            return {}
        list_resources = getattr(self._resource_service, "list_resources", None)
        if not callable(list_resources):
            return {}
        return {
            resource.id: resource
            for resource in list_resources()
        }

    @staticmethod
    def _resource_name_for_assignment(assignment, *, resources_by_id: dict[str, object]) -> str:
        resource = resources_by_id.get(assignment.resource_id)
        return str(
            getattr(resource, "name", "") or getattr(assignment, "resource_id", "")
        )

    @staticmethod
    def _serialize_task(task, *, project_name: str) -> TaskDesktopDto:
        return TaskDesktopDto(
            id=task.id,
            project_id=task.project_id,
            project_name=project_name,
            name=task.name,
            description=task.description or "",
            status=task.status.value,
            status_label=task.status.value.replace("_", " ").title(),
            start_date=task.start_date,
            end_date=task.end_date,
            duration_days=task.duration_days,
            priority=task.priority,
            percent_complete=float(task.percent_complete or 0.0),
            actual_start=task.actual_start,
            actual_end=task.actual_end,
            deadline=task.deadline,
            version=task.version,
        )

    @classmethod
    def _serialize_assignment(
        cls,
        assignment,
        *,
        resources_by_id: dict[str, object],
    ) -> TaskAssignmentDesktopDto:
        return TaskAssignmentDesktopDto(
            id=assignment.id,
            task_id=assignment.task_id,
            resource_id=assignment.resource_id,
            resource_name=cls._resource_name_for_assignment(
                assignment,
                resources_by_id=resources_by_id,
            ),
            allocation_percent=float(getattr(assignment, "allocation_percent", 0.0) or 0.0),
            hours_logged=float(getattr(assignment, "hours_logged", 0.0) or 0.0),
            project_resource_id=getattr(assignment, "project_resource_id", None),
        )

    @staticmethod
    def _serialize_dependency(
        dependency,
        *,
        current_task_id: str,
        tasks_by_id: dict[str, object],
    ) -> TaskDependencyDesktopDto:
        direction, linked_task_id = _dependency_direction(current_task_id, dependency)
        predecessor = tasks_by_id.get(dependency.predecessor_task_id)
        successor = tasks_by_id.get(dependency.successor_task_id)
        predecessor_name = str(
            getattr(predecessor, "name", "") or dependency.predecessor_task_id
        )
        successor_name = str(
            getattr(successor, "name", "") or dependency.successor_task_id
        )
        linked_task_name = str(
            getattr(tasks_by_id.get(linked_task_id), "name", "") or linked_task_id
        )
        return TaskDependencyDesktopDto(
            id=dependency.id,
            direction=direction,
            direction_label="Predecessor" if direction == "PREDECESSOR" else "Successor",
            linked_task_id=linked_task_id,
            linked_task_name=linked_task_name,
            dependency_type=dependency.dependency_type.value,
            dependency_type_label=_dependency_type_label(dependency.dependency_type),
            lag_days=int(getattr(dependency, "lag_days", 0) or 0),
            relationship_label=f"{predecessor_name} -> {successor_name}",
        )


    @staticmethod
    def _serialize_reservation(reservation) -> TaskReservationDesktopDto:
        status_value = str(
            getattr(getattr(reservation, "status", None), "value", None)
            or getattr(reservation, "status", "")
            or ""
        )
        return TaskReservationDesktopDto(
            id=reservation.id,
            reservation_number=str(getattr(reservation, "reservation_number", "") or ""),
            stock_item_id=str(getattr(reservation, "stock_item_id", "") or ""),
            storeroom_id=str(getattr(reservation, "storeroom_id", "") or ""),
            reserved_qty=float(getattr(reservation, "reserved_qty", 0.0) or 0.0),
            issued_qty=float(getattr(reservation, "issued_qty", 0.0) or 0.0),
            remaining_qty=float(getattr(reservation, "remaining_qty", 0.0) or 0.0),
            uom=str(getattr(reservation, "uom", "") or ""),
            status=status_value,
            status_label=status_value.replace("_", " ").title(),
            need_by_date=getattr(reservation, "need_by_date", None),
            notes=str(getattr(reservation, "notes", "") or ""),
        )


def build_project_management_tasks_desktop_api(
    *,
    project_service: ProjectService | None = None,
    task_service: TaskService | None = None,
    project_resource_service: ProjectResourceService | None = None,
    resource_service: ResourceService | None = None,
    reservation_service: object | None = None,
) -> ProjectManagementTasksDesktopApi:
    return ProjectManagementTasksDesktopApi(
        project_service=project_service,
        task_service=task_service,
        project_resource_service=project_resource_service,
        resource_service=resource_service,
        reservation_service=reservation_service,
    )


def _coerce_task_status(value: str | TaskStatus | None) -> TaskStatus:
    if isinstance(value, TaskStatus):
        return value
    normalized_value = str(value or TaskStatus.TODO.value).strip().upper()
    try:
        return TaskStatus(normalized_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported task status: {normalized_value}.") from exc


def _coerce_dependency_type(
    value: str | DependencyType | None,
) -> DependencyType:
    if isinstance(value, DependencyType):
        return value
    normalized_value = str(value or DependencyType.FINISH_TO_START.value).strip().upper()
    try:
        return DependencyType(normalized_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported dependency type: {normalized_value}.") from exc


def _coerce_dependency_direction(value: str | None) -> str:
    normalized_value = str(value or "predecessor").strip().upper()
    if normalized_value in {"PREDECESSOR", "CURRENT_DEPENDS_ON_OTHER"}:
        return "PREDECESSOR"
    if normalized_value in {"SUCCESSOR", "OTHER_DEPENDS_ON_CURRENT"}:
        return "SUCCESSOR"
    raise ValueError(f"Unsupported dependency direction: {normalized_value}.")


def _dependency_direction(current_task_id: str, dependency) -> tuple[str, str]:
    if current_task_id == dependency.successor_task_id:
        return ("PREDECESSOR", dependency.predecessor_task_id)
    if current_task_id == dependency.predecessor_task_id:
        return ("SUCCESSOR", dependency.successor_task_id)
    return ("", dependency.successor_task_id)


def _dependency_type_label(value: DependencyType | str) -> str:
    dependency_type = _coerce_dependency_type(value)
    labels = {
        DependencyType.FINISH_TO_START: "Finish -> Start",
        DependencyType.FINISH_TO_FINISH: "Finish -> Finish",
        DependencyType.START_TO_START: "Start -> Start",
        DependencyType.START_TO_FINISH: "Start -> Finish",
    }
    return labels[dependency_type]


def _normalize_task_ids(task_ids) -> tuple[str, ...]:
    normalized_ids: list[str] = []
    seen: set[str] = set()
    for task_id in task_ids or ():
        normalized_id = str(task_id or "").strip()
        if not normalized_id or normalized_id in seen:
            continue
        normalized_ids.append(normalized_id)
        seen.add(normalized_id)
    return tuple(normalized_ids)


__all__ = [
    "ProjectManagementTasksDesktopApi",
    "TaskAssignmentAllocationCommand",
    "TaskAssignmentCreateCommand",
    "TaskAssignmentDesktopDto",
    "TaskAssignmentHoursCommand",
    "TaskBulkStatusCommand",
    "TaskCreateCommand",
    "TaskDesktopDto",
    "TaskDependencyCreateCommand",
    "TaskDependencyDesktopDto",
    "TaskDependencyTypeDescriptor",
    "TaskMaterialDemandSummary",
    "TaskProgressCommand",
    "TaskProjectOptionDescriptor",
    "TaskProjectResourceOptionDescriptor",
    "TaskReservationCreateCommand",
    "TaskReservationDesktopDto",
    "TaskStatusDescriptor",
    "TaskUpdateCommand",
    "build_project_management_tasks_desktop_api",
]
