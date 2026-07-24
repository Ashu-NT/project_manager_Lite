"""ProjectManagementProjectsDesktopApi — thin projects desktop facade."""

from __future__ import annotations

from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    ProjectResourceService,
    ResourceService,
)
from src.core.platform.site import SiteService
from src.core.platform.common.exceptions import BusinessRuleError

from src.core.modules.project_management.api.desktop.projects.models.project import (
    ProjectDesktopDto,
    ProjectStatusDescriptor,
)
from src.core.modules.project_management.api.desktop.projects.models.resources import (
    ProjectAssignableResourceOptionDescriptor,
    ProjectResourceDesktopDto,
)
from src.core.modules.project_management.api.desktop.projects.commands.project_commands import (
    ProjectCreateCommand,
    ProjectUpdateCommand,
)
from src.core.modules.project_management.api.desktop.projects.commands.resource_commands import (
    ProjectResourceAssignCommand,
    ProjectResourceUpdateCommand,
)
from src.core.modules.project_management.api.desktop.projects.builders.status_builder import build_status_options
from src.core.modules.project_management.api.desktop.projects.builders.resource_builder import (
    build_assignable_options,
    list_resources_for_context,
    resource_lookup,
)
from src.core.modules.project_management.api.desktop.projects.serializers.project_serializer import serialize_project
from src.core.modules.project_management.api.desktop.projects.serializers.resource_serializer import (
    serialize_project_resource,
)
from src.core.modules.project_management.api.desktop.projects.services.access_service import (
    can_fallback_project_access,
    resolve_user_session,
)
from src.core.modules.project_management.api.desktop.projects.utils.project_utils import (
    call_with_supported_kwargs,
    coerce_project_status,
)


class ProjectManagementProjectsDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        project_resource_service: ProjectResourceService | None = None,
        resource_service: ResourceService | None = None,
        site_service: SiteService | None = None,
    ) -> None:
        self._project_service = project_service
        self._project_resource_service = project_resource_service
        self._resource_service = resource_service
        self._site_service = site_service

    # ── Status options ────────────────────────────────────────────────────────

    def list_statuses(self) -> tuple[ProjectStatusDescriptor, ...]:
        return build_status_options()

    # ── Project CRUD ──────────────────────────────────────────────────────────

    def list_projects(self) -> tuple[ProjectDesktopDto, ...]:
        if self._project_service is None:
            return ()
        site_lookup = self._site_lookup()
        projects = sorted(
            self._project_service.list_projects(),
            key=lambda p: (p.name or "").casefold(),
        )
        return tuple(serialize_project(p, site_lookup=site_lookup) for p in projects)

    def list_projects_by_status(self, status: str) -> tuple[ProjectDesktopDto, ...]:
        if self._project_service is None:
            return ()
        site_lookup = self._site_lookup()
        projects = sorted(
            self._project_service.list_projects_by_status(coerce_project_status(status)),
            key=lambda p: (p.name or "").casefold(),
        )
        return tuple(serialize_project(p, site_lookup=site_lookup) for p in projects)

    def search_projects(self, query: str) -> tuple[ProjectDesktopDto, ...]:
        if self._project_service is None or not query:
            return ()
        site_lookup = self._site_lookup()
        projects = sorted(
            self._project_service.search_projects_by_name(query),
            key=lambda p: (p.name or "").casefold(),
        )
        return tuple(serialize_project(p, site_lookup=site_lookup) for p in projects)

    def create_project(self, command: ProjectCreateCommand) -> ProjectDesktopDto:
        service = self._require_project_service()
        project = call_with_supported_kwargs(
            service.create_project,
            name=command.name,
            code=getattr(command, "code", ""),
            description=command.description,
            status=coerce_project_status(command.status),
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
        return serialize_project(project, site_lookup=self._site_lookup())

    def update_project(self, command: ProjectUpdateCommand) -> ProjectDesktopDto:
        service = self._require_project_service()
        project = call_with_supported_kwargs(
            service.update_project,
            command.project_id,
            expected_version=command.expected_version,
            name=command.name,
            code=getattr(command, "code", ""),
            description=command.description,
            status=coerce_project_status(command.status),
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
        return serialize_project(project, site_lookup=self._site_lookup())

    def set_project_status(self, project_id: str, status: str) -> ProjectDesktopDto:
        service = self._require_project_service()
        service.set_status(project_id, coerce_project_status(status))
        project = service.get_project(project_id)
        if project is None:
            raise RuntimeError("Project status updated but the project could not be reloaded.")
        return serialize_project(project, site_lookup=self._site_lookup())

    def delete_project(self, project_id: str) -> None:
        self._require_project_service().delete_project(project_id)

    # ── Project resources ─────────────────────────────────────────────────────

    def list_project_resources(self, project_id: str) -> tuple[ProjectResourceDesktopDto, ...]:
        normalized_id = str(project_id or "").strip()
        if not normalized_id or self._project_resource_service is None:
            return ()
        list_by_project = getattr(self._project_resource_service, "list_by_project", None)
        if not callable(list_by_project):
            return ()
        try:
            project_resources = list(list_by_project(normalized_id))
        except BusinessRuleError as exc:
            if not self._can_fallback(normalized_id, exc):
                raise
            pr_repo = getattr(self._project_resource_service, "_project_resource_repo", None)
            if pr_repo is None:
                return ()
            project_resources = list(pr_repo.list_by_project(normalized_id))

        resource_ids = tuple(str(getattr(pr, "resource_id", "") or "") for pr in project_resources)
        resources_by_id = resource_lookup(
            normalized_id, resource_ids,
            resource_service=self._resource_service,
            can_fallback_fn=self._can_fallback,
        )
        rows = [
            serialize_project_resource(
                pr,
                resource_by_id=resources_by_id.get(str(getattr(pr, "resource_id", "") or "")),
            )
            for pr in project_resources
        ]
        return tuple(sorted(rows, key=lambda r: (not r.is_active, r.resource_name.casefold())))

    def list_assignable_resources(self, project_id: str) -> tuple[ProjectAssignableResourceOptionDescriptor, ...]:
        normalized_id = str(project_id or "").strip()
        if not normalized_id:
            return ()
        assigned_ids = {row.resource_id for row in self.list_project_resources(normalized_id)}
        return build_assignable_options(
            normalized_id, assigned_ids,
            resource_service=self._resource_service,
            can_fallback_fn=self._can_fallback,
        )

    def add_project_resource(self, command: ProjectResourceAssignCommand) -> ProjectResourceDesktopDto:
        normalized_project_id = str(command.project_id or "").strip()
        normalized_resource_id = str(command.resource_id or "").strip()
        if not normalized_project_id:
            raise ValueError("Project ID is required to assign a resource.")
        if not normalized_resource_id:
            raise ValueError("Resource selection is required.")
        service = self._require_project_resource_service()
        add_fn = getattr(service, "add_to_project", None) or getattr(service, "create", None)
        if not callable(add_fn):
            raise RuntimeError("Project resource service does not support project assignment.")
        project_resource = add_fn(
            project_id=normalized_project_id,
            resource_id=normalized_resource_id,
            hourly_rate=command.hourly_rate,
            currency_code=command.currency_code,
            planned_hours=command.planned_hours,
            is_active=True,
        )
        res = resource_lookup(
            normalized_project_id, (normalized_resource_id,),
            resource_service=self._resource_service,
            can_fallback_fn=self._can_fallback,
        ).get(normalized_resource_id)
        return serialize_project_resource(project_resource, resource_by_id=res)

    def update_project_resource(self, command: ProjectResourceUpdateCommand) -> None:
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

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _require_project_service(self) -> ProjectService:
        if self._project_service is None:
            raise RuntimeError("Project management projects desktop API is not connected.")
        return self._project_service

    def _require_project_resource_service(self) -> ProjectResourceService:
        if self._project_resource_service is None:
            raise RuntimeError("Project management project-resource desktop API is not connected.")
        return self._project_resource_service

    def _site_lookup(self) -> dict[str, str]:
        if self._site_service is None:
            return {}
        try:
            return {
                str(site.id): str(getattr(site, "name", "") or "").strip()
                for site in self._site_service.list_sites(active_only=None)
                if getattr(site, "id", None)
            }
        except Exception:
            return {}

    def _can_fallback(self, project_id: str, exc: BusinessRuleError) -> bool:
        user_session = resolve_user_session(
            project_service=self._project_service,
            project_resource_service=self._project_resource_service,
            resource_service=self._resource_service,
        )
        return can_fallback_project_access(project_id, exc, user_session=user_session)


__all__ = ["ProjectManagementProjectsDesktopApi"]
