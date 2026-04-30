from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.domain.enums import TaskStatus


@dataclass(frozen=True)
class TaskProjectOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class TaskStatusDescriptor:
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


class ProjectManagementTasksDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        task_service: TaskService | None = None,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service

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

    def delete_task(self, task_id: str) -> None:
        self._require_task_service().delete_task(task_id)

    def _require_task_service(self) -> TaskService:
        if self._task_service is None:
            raise RuntimeError("Project management tasks desktop API is not connected.")
        return self._task_service

    def _project_name_by_id(self) -> dict[str, str]:
        if self._project_service is None:
            return {}
        return {
            project.id: project.name
            for project in self._project_service.list_projects()
        }

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


def build_project_management_tasks_desktop_api(
    *,
    project_service: ProjectService | None = None,
    task_service: TaskService | None = None,
) -> ProjectManagementTasksDesktopApi:
    return ProjectManagementTasksDesktopApi(
        project_service=project_service,
        task_service=task_service,
    )


def _coerce_task_status(value: str | TaskStatus | None) -> TaskStatus:
    if isinstance(value, TaskStatus):
        return value
    normalized_value = str(value or TaskStatus.TODO.value).strip().upper()
    try:
        return TaskStatus(normalized_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported task status: {normalized_value}.") from exc


__all__ = [
    "ProjectManagementTasksDesktopApi",
    "TaskCreateCommand",
    "TaskDesktopDto",
    "TaskProgressCommand",
    "TaskProjectOptionDescriptor",
    "TaskStatusDescriptor",
    "TaskUpdateCommand",
    "build_project_management_tasks_desktop_api",
]
