from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import inspect

from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    ProjectResourceService,
    ResourceService,
)
from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.platform.common.exceptions import BusinessRuleError


@dataclass(frozen=True)
class ProjectStatusDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class ProjectDesktopDto:
    id: str
    name: str
    code: str
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
    code: str = ""
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
    code: str = ""
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


@dataclass(frozen=True)
class ProjectResourceDesktopDto:
    id: str
    project_id: str
    resource_id: str
    resource_name: str
    role: str
    worker_type_label: str
    hourly_rate: float | None
    hourly_rate_label: str
    currency_code: str | None
    planned_hours: float
    planned_hours_label: str
    is_active: bool
    status_label: str


@dataclass(frozen=True)
class ProjectAssignableResourceOptionDescriptor:
    value: str
    label: str


@dataclass(frozen=True)
class ProjectResourceAssignCommand:
    project_id: str
    resource_id: str
    planned_hours: float = 0.0
    hourly_rate: float | None = None
    currency_code: str | None = None


@dataclass(frozen=True)
class ProjectResourceUpdateCommand:
    project_resource_id: str
    planned_hours: float = 0.0
    hourly_rate: float | None = None
    is_active: bool = True


class ProjectManagementProjectsDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        project_resource_service: ProjectResourceService | None = None,
        resource_service: ResourceService | None = None,
    ) -> None:
        self._project_service = project_service
        self._project_resource_service = project_resource_service
        self._resource_service = resource_service

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
        desired_status = _coerce_project_status(command.status)
        project = _call_with_supported_kwargs(
            service.create_project,
            name=command.name,
            code=getattr(command, "code", ""),
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
        return self._serialize_project(project)

    def update_project(self, command: ProjectUpdateCommand) -> ProjectDesktopDto:
        service = self._require_project_service()
        project = _call_with_supported_kwargs(
            service.update_project,
            command.project_id,
            expected_version=command.expected_version,
            name=command.name,
            code=getattr(command, "code", ""),
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

    def list_project_resources(
        self,
        project_id: str,
    ) -> tuple[ProjectResourceDesktopDto, ...]:
        normalized_project_id = str(project_id or "").strip()
        if (
            not normalized_project_id
            or self._project_resource_service is None
        ):
            return ()
        list_by_project = getattr(self._project_resource_service, "list_by_project", None)
        if not callable(list_by_project):
            return ()
        try:
            project_resources = list(list_by_project(normalized_project_id))
        except BusinessRuleError as exc:
            if not self._can_fallback_project_access(normalized_project_id, exc):
                raise
            project_resource_repo = getattr(
                self._project_resource_service,
                "_project_resource_repo",
                None,
            )
            if project_resource_repo is None:
                return ()
            project_resources = list(project_resource_repo.list_by_project(normalized_project_id))

        resources_by_id = self._resource_lookup(
            project_id=normalized_project_id,
            resource_ids=tuple(
                str(getattr(project_resource, "resource_id", "") or "")
                for project_resource in project_resources
            ),
        )
        rows = [
            self._serialize_project_resource(
                project_resource,
                resource_by_id=resources_by_id.get(
                    str(getattr(project_resource, "resource_id", "") or "")
                ),
            )
            for project_resource in project_resources
        ]
        return tuple(
            sorted(
                rows,
                key=lambda row: (
                    not row.is_active,
                    row.resource_name.casefold(),
                ),
            )
        )

    def list_assignable_resources(
        self,
        project_id: str,
    ) -> tuple[ProjectAssignableResourceOptionDescriptor, ...]:
        normalized_project_id = str(project_id or "").strip()
        if not normalized_project_id:
            return ()

        assigned_resource_ids = {
            row.resource_id
            for row in self.list_project_resources(normalized_project_id)
        }
        resources = self._list_resources_for_project_context(normalized_project_id)
        options = [
            ProjectAssignableResourceOptionDescriptor(
                value=str(resource.id),
                label=self._assignable_resource_label(resource),
            )
            for resource in resources
            if getattr(resource, "id", None)
            and bool(getattr(resource, "is_active", True))
            and str(resource.id) not in assigned_resource_ids
        ]
        return tuple(
            sorted(options, key=lambda option: option.label.casefold())
        )

    def add_project_resource(
        self,
        command: ProjectResourceAssignCommand,
    ) -> ProjectResourceDesktopDto:
        normalized_project_id = str(command.project_id or "").strip()
        normalized_resource_id = str(command.resource_id or "").strip()
        if not normalized_project_id:
            raise ValueError("Project ID is required to assign a resource.")
        if not normalized_resource_id:
            raise ValueError("Resource selection is required.")
        service = self._require_project_resource_service()
        add_to_project = getattr(service, "add_to_project", None)
        if callable(add_to_project):
            project_resource = add_to_project(
                project_id=normalized_project_id,
                resource_id=normalized_resource_id,
                hourly_rate=command.hourly_rate,
                currency_code=command.currency_code,
                planned_hours=command.planned_hours,
                is_active=True,
            )
        else:
            create = getattr(service, "create", None)
            if not callable(create):
                raise RuntimeError(
                    "Project resource service does not support project assignment."
                )
            project_resource = create(
                project_id=normalized_project_id,
                resource_id=normalized_resource_id,
                hourly_rate=command.hourly_rate,
                currency_code=command.currency_code,
                planned_hours=command.planned_hours,
                is_active=True,
            )
        resource_by_id = self._resource_lookup(
            project_id=normalized_project_id,
            resource_ids=(normalized_resource_id,),
        ).get(normalized_resource_id)
        return self._serialize_project_resource(
            project_resource,
            resource_by_id=resource_by_id,
        )

    def update_project_resource(
        self,
        command: ProjectResourceUpdateCommand,
    ) -> None:
        normalized_id = str(command.project_resource_id or "").strip()
        if not normalized_id:
            raise ValueError("Project resource ID is required.")
        service = self._require_project_resource_service()
        update = getattr(service, "update", None)
        if not callable(update):
            raise RuntimeError("Project resource service does not support updates.")
        update(
            normalized_id,
            hourly_rate=command.hourly_rate,
            currency_code=None,
            planned_hours=max(0.0, command.planned_hours),
            is_active=command.is_active,
        )

    def remove_project_resource(self, project_resource_id: str) -> None:
        normalized_id = str(project_resource_id or "").strip()
        if not normalized_id:
            raise ValueError("Project resource ID is required.")
        service = self._require_project_resource_service()
        delete = getattr(service, "delete", None)
        if not callable(delete):
            raise RuntimeError("Project resource service does not support deletion.")
        delete(normalized_id)

    def _require_project_service(self) -> ProjectService:
        if self._project_service is None:
            raise RuntimeError(
                "Project management projects desktop API is not connected."
            )
        return self._project_service

    def _require_project_resource_service(self) -> ProjectResourceService:
        if self._project_resource_service is None:
            raise RuntimeError(
                "Project management project-resource desktop API is not connected."
            )
        return self._project_resource_service

    @staticmethod
    def _serialize_project(project) -> ProjectDesktopDto:
        resolved_currency = (project.currency or "").strip().upper() or None
        return ProjectDesktopDto(
            id=project.id,
            name=project.name,
            code=getattr(project, "code", "") or "",
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

    def _resource_lookup(
        self,
        *,
        project_id: str,
        resource_ids: tuple[str, ...],
    ) -> dict[str, object]:
        resources = self._list_resources_for_project_context(
            project_id,
            resource_ids=resource_ids,
        )
        return {
            str(resource.id): resource
            for resource in resources
            if resource is not None and getattr(resource, "id", None)
        }

    def _list_resources_for_project_context(
        self,
        project_id: str,
        *,
        resource_ids: tuple[str, ...] | None = None,
    ) -> tuple[object, ...]:
        if self._resource_service is None:
            return ()
        list_resources = getattr(self._resource_service, "list_resources", None)
        if not callable(list_resources):
            return ()
        try:
            resources = list(list_resources())
        except BusinessRuleError as exc:
            if not self._can_fallback_project_access(project_id, exc):
                raise
            resource_repo = getattr(self._resource_service, "_resource_repo", None)
            if resource_repo is None:
                return ()
            normalized_ids = tuple(
                {
                    str(resource_id or "").strip()
                    for resource_id in (resource_ids or ())
                    if str(resource_id or "").strip()
                }
            )
            if normalized_ids:
                resources = [
                    resource_repo.get(resource_id)
                    for resource_id in normalized_ids
                ]
            else:
                resources = list(resource_repo.list_all())
        return tuple(resource for resource in resources if resource is not None)

    def _project_user_session(self):
        for service in (
            self._project_resource_service,
            self._resource_service,
            self._project_service,
        ):
            if service is not None:
                user_session = getattr(service, "_user_session", None)
                if user_session is not None:
                    return user_session
        return None

    def _can_fallback_project_access(
        self,
        project_id: str,
        exc: BusinessRuleError,
    ) -> bool:
        message = str(exc)
        if "project.read" not in message and "resource.read" not in message:
            return False
        normalized_project_id = str(project_id or "").strip()
        if not normalized_project_id:
            return False
        user_session = self._project_user_session()
        if user_session is None:
            return False
        if user_session.has_project_permission(normalized_project_id, "project.manage"):
            return True
        if user_session.has_project_permission(normalized_project_id, "project.read"):
            return True
        if (
            not user_session.is_project_restricted()
            and (
                user_session.has_permission("project.manage")
                or user_session.has_permission("project.read")
            )
        ):
            return True
        return False

    @staticmethod
    def _serialize_project_resource(
        project_resource,
        *,
        resource_by_id,
    ) -> ProjectResourceDesktopDto:
        resolved_currency = (
            str(
                getattr(project_resource, "currency_code", None)
                or getattr(resource_by_id, "currency_code", None)
                or ""
            ).strip().upper()
            or None
        )
        resolved_rate = (
            getattr(project_resource, "hourly_rate", None)
            if getattr(project_resource, "hourly_rate", None) is not None
            else getattr(resource_by_id, "hourly_rate", None)
        )
        worker_type_raw = str(getattr(resource_by_id, "worker_type", "") or "")
        worker_type_label = worker_type_raw.replace("_", " ").title() if worker_type_raw else "Unknown"
        is_active = bool(getattr(project_resource, "is_active", True))
        return ProjectResourceDesktopDto(
            id=str(getattr(project_resource, "id", "") or ""),
            project_id=str(getattr(project_resource, "project_id", "") or ""),
            resource_id=str(getattr(project_resource, "resource_id", "") or ""),
            resource_name=str(
                getattr(resource_by_id, "name", "")
                or getattr(project_resource, "resource_id", "")
                or "Unknown resource"
            ),
            role=str(getattr(resource_by_id, "role", "") or ""),
            worker_type_label=worker_type_label,
            hourly_rate=resolved_rate,
            hourly_rate_label=_format_hourly_rate(resolved_rate, resolved_currency),
            currency_code=resolved_currency,
            planned_hours=float(getattr(project_resource, "planned_hours", 0.0) or 0.0),
            planned_hours_label=_format_hours(
                float(getattr(project_resource, "planned_hours", 0.0) or 0.0)
            ),
            is_active=is_active,
            status_label="Active" if is_active else "Inactive",
        )

    @staticmethod
    def _assignable_resource_label(resource) -> str:
        name = str(getattr(resource, "name", "") or "Unnamed resource")
        role = str(getattr(resource, "role", "") or "")
        hourly_rate = getattr(resource, "hourly_rate", None)
        currency_code = str(getattr(resource, "currency_code", "") or "").strip().upper() or None
        details: list[str] = []
        if role:
            details.append(role)
        if hourly_rate is not None:
            details.append(_format_hourly_rate(hourly_rate, currency_code))
        return f"{name} | {' | '.join(details)}" if details else name


def build_project_management_projects_desktop_api(
    *,
    project_service: ProjectService | None = None,
    project_resource_service: ProjectResourceService | None = None,
    resource_service: ResourceService | None = None,
) -> ProjectManagementProjectsDesktopApi:
    return ProjectManagementProjectsDesktopApi(
        project_service=project_service,
        project_resource_service=project_resource_service,
        resource_service=resource_service,
    )


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


def _format_hourly_rate(value: float | None, currency: str | None) -> str:
    if value is None:
        return "Rate not set"
    amount = f"{float(value):,.2f}"
    resolved_currency = (currency or "").strip().upper()
    if resolved_currency:
        return f"{amount} {resolved_currency}/hr"
    return f"{amount}/hr"


def _format_hours(value: float | None) -> str:
    if value is None:
        return "0.0 h"
    return f"{float(value):,.1f} h"


__all__ = [
    "ProjectCreateCommand",
    "ProjectAssignableResourceOptionDescriptor",
    "ProjectDesktopDto",
    "ProjectManagementProjectsDesktopApi",
    "ProjectResourceAssignCommand",
    "ProjectResourceUpdateCommand",
    "ProjectResourceDesktopDto",
    "ProjectStatusDescriptor",
    "ProjectUpdateCommand",
    "build_project_management_projects_desktop_api",
]
