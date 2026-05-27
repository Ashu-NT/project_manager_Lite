from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import inspect

from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.domain.enums import ProjectStatus


@dataclass(frozen=True)
class ProjectStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class ProjectDesktopDto:
    id: str
    name: str
    description: str
    status: str
    status_label: str
    start_date: date | None
    end_date: date | None
    client_name: str | None
    client_contact: str | None
    planned_budget: float | None
    planned_budget_label: str
    currency: str | None
    organization_id: str | None
    site_id: str | None
    client_party_id: str | None
    manager_user_id: str | None
    version: int


@dataclass(frozen=True)
class ProjectCreateCommand:
    name: str
    description: str = ""
    status: str = ProjectStatus.PLANNED.value
    client_name: str | None = None
    client_contact: str | None = None
    planned_budget: float | None = None
    currency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    organization_id: str | None = None
    site_id: str | None = None
    client_party_id: str | None = None
    manager_user_id: str | None = None


@dataclass(frozen=True)
class ProjectUpdateCommand:
    project_id: str
    name: str
    description: str = ""
    status: str = ProjectStatus.PLANNED.value
    client_name: str | None = None
    client_contact: str | None = None
    planned_budget: float | None = None
    currency: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    organization_id: str | None = None
    site_id: str | None = None
    client_party_id: str | None = None
    manager_user_id: str | None = None
    expected_version: int | None = None


class ProjectManagementProjectsDesktopApi:
    def __init__(self, *, project_service: ProjectService | None = None) -> None:
        self._project_service = project_service

    def list_statuses(self) -> tuple[ProjectStatusDescriptor, ...]:
        return tuple(
            ProjectStatusDescriptor(
                value=status.value,
                label=status.value.replace("_", " ").title(),
            )
            for status in ProjectStatus
        )

    def list_projects(self) -> tuple[ProjectDesktopDto, ...]:
        if self._project_service is None:
            return ()
        projects = sorted(
            self._project_service.list_projects(),
            key=lambda project: (project.name or "").casefold(),
        )
        return tuple(self._serialize_project(project) for project in projects)

    def create_project(self, command: ProjectCreateCommand) -> ProjectDesktopDto:
        service = self._require_project_service()
        project = _call_with_supported_kwargs(
            service.create_project,
            name=command.name,
            description=command.description,
            status=desired_status,
            client_name=command.client_name,
            client_contact=command.client_contact,
            planned_budget=command.planned_budget,
            currency=command.currency,
            start_date=command.start_date,
            end_date=command.end_date,
            organization_id=getattr(command, "organization_id", None),
            site_id=getattr(command, "site_id", None),
            client_party_id=getattr(command, "client_party_id", None),
            manager_user_id=getattr(command, "manager_user_id", None),
        )
        desired_status = _coerce_project_status(command.status)
        return self._serialize_project(project)

    def update_project(self, command: ProjectUpdateCommand) -> ProjectDesktopDto:
        service = self._require_project_service()
        project = _call_with_supported_kwargs(
            service.update_project,
            command.project_id,
            expected_version=command.expected_version,
            name=command.name,
            description=command.description,
            status=_coerce_project_status(command.status),
            start_date=command.start_date,
            end_date=command.end_date,
            client_name=command.client_name,
            client_contact=command.client_contact,
            planned_budget=command.planned_budget,
            currency=command.currency,
            organization_id=getattr(command, "organization_id", None),
            site_id=getattr(command, "site_id", None),
            client_party_id=getattr(command, "client_party_id", None),
            manager_user_id=getattr(command, "manager_user_id", None),
        )
        return self._serialize_project(project)

    def set_project_status(self, project_id: str, status: str) -> ProjectDesktopDto:
        service = self._require_project_service()
        service.set_status(project_id, _coerce_project_status(status))
        project = service.get_project(project_id)
        if project is None:
            raise RuntimeError("Project status updated but the project could not be reloaded.")
        return self._serialize_project(project)

    def delete_project(self, project_id: str) -> None:
        self._require_project_service().delete_project(project_id)

    def _require_project_service(self) -> ProjectService:
        if self._project_service is None:
            raise RuntimeError(
                "Project management projects desktop API is not connected."
            )
        return self._project_service

    @staticmethod
    def _serialize_project(project) -> ProjectDesktopDto:
        resolved_currency = (project.currency or "").strip().upper() or None
        return ProjectDesktopDto(
            id=project.id,
            name=project.name,
            description=project.description or "",
            status=project.status.value,
            status_label=project.status.value.replace("_", " ").title(),
            start_date=project.start_date,
            end_date=project.end_date,
            client_name=project.client_name,
            client_contact=project.client_contact,
            planned_budget=project.planned_budget,
            planned_budget_label=_format_budget(
                project.planned_budget,
                resolved_currency,
            ),
            currency=resolved_currency,
            organization_id=getattr(project, "organization_id", None),
            site_id=getattr(project, "site_id", None),
            client_party_id=getattr(project, "client_party_id", None),
            manager_user_id=getattr(project, "manager_user_id", None),
            version=project.version,
        )


def build_project_management_projects_desktop_api(
    *,
    project_service: ProjectService | None = None,
) -> ProjectManagementProjectsDesktopApi:
    return ProjectManagementProjectsDesktopApi(project_service=project_service)


def _coerce_project_status(value: str | ProjectStatus | None) -> ProjectStatus:
    if isinstance(value, ProjectStatus):
        return value
    normalized_value = str(value or ProjectStatus.PLANNED.value).strip().upper()
    try:
        return ProjectStatus(normalized_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported project status: {normalized_value}.") from exc


def _call_with_supported_kwargs(method, *args, **kwargs):
    parameters = inspect.signature(method).parameters
    if any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    ):
        return method(*args, **kwargs)
    supported_kwargs = {
        name: value
        for name, value in kwargs.items()
        if name in parameters
    }
    return method(*args, **supported_kwargs)


def _format_budget(value: float | None, currency: str | None) -> str:
    if value is None:
        return "Not set"
    amount = f"{float(value):,.2f}"
    resolved_currency = (currency or "").strip().upper()
    if resolved_currency:
        return f"{resolved_currency} {amount}"
    return amount


__all__ = [
    "ProjectCreateCommand",
    "ProjectDesktopDto",
    "ProjectManagementProjectsDesktopApi",
    "ProjectStatusDescriptor",
    "ProjectUpdateCommand",
    "build_project_management_projects_desktop_api",
]
