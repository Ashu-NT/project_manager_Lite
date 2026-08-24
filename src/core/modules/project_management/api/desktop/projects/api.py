"""ProjectManagementProjectsDesktopApi — thin projects desktop facade."""

from __future__ import annotations

from decimal import Decimal

from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    ProjectResourceService,
    ResourceService,
)
from src.core.platform.application.master_data.site.site_service import SiteService
from src.core.platform.application.master_data.department.department_service import DepartmentService

from src.core.modules.project_management.api.desktop.projects.models.project import (
    ProjectCatalogPageDesktopDto,
    ProjectDesktopDto,
    ProjectStatusDescriptor,
)
from src.core.modules.project_management.api.desktop.projects.models.resources import (
    ProjectAssignableResourceOptionDescriptor,
    ProjectResourceDesktopDto,
    ProjectResourceDetailDesktopDto,
    ProjectResourceDetailPageDesktopDto,
    ProjectResourceUsageDesktopDto,
)
from src.core.modules.project_management.api.desktop.common.detail_pages import (
    DetailActivityDesktopDto,
    DetailActivityPageDesktopDto,
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
    serialize_project_resource_usage,
)
from src.core.modules.project_management.api.desktop.projects.utils.project_utils import (
    coerce_project_status,
    optional_date,
)


class ProjectManagementProjectsDesktopApi:
    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        project_resource_service: ProjectResourceService | None = None,
        resource_service: ResourceService | None = None,
        site_service: SiteService | None = None,
        department_service: DepartmentService | None = None,
    ) -> None:
        self._project_service = project_service
        self._project_resource_service = project_resource_service
        self._resource_service = resource_service
        self._site_service = site_service
        self._department_service = department_service

    # ── Status options ────────────────────────────────────────────────────────

    def list_statuses(self) -> tuple[ProjectStatusDescriptor, ...]:
        return build_status_options()

    # ── Project CRUD ──────────────────────────────────────────────────────────

    def list_projects(self) -> tuple[ProjectDesktopDto, ...]:
        if self._project_service is None:
            return ()
        site_lookup = self._site_lookup()
        department_lookup = self._department_lookup()
        projects = sorted(
            self._project_service.list_projects(),
            key=lambda p: (p.name or "").casefold(),
        )
        return tuple(
            serialize_project(p, site_lookup=site_lookup, department_lookup=department_lookup)
            for p in projects
        )

    def list_project_page(
        self,
        *,
        search_text: str = "",
        status: str = "all",
        project_name: str = "",
        client_name: str = "",
        site_id: str = "all",
        department_id: str = "all",
        manager_user_id: str = "all",
        start_date_from: str = "",
        start_date_to: str = "",
        end_date_from: str = "",
        end_date_to: str = "",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "title",
        sort_direction: str = "asc",
    ) -> ProjectCatalogPageDesktopDto:
        service = self._require_project_service()
        normalized_status = str(status or "all").strip().lower()
        status_value = (
            None
            if normalized_status == "all"
            else coerce_project_status(normalized_status)
        )
        normalized_site_id = str(site_id or "all").strip()
        normalized_department_id = str(department_id or "all").strip()
        normalized_manager_id = str(manager_user_id or "all").strip()
        result = service.query_catalog_page(
            search_text=search_text,
            status=status_value,
            project_name=str(project_name or "").strip() or None,
            client_name=str(client_name or "").strip() or None,
            site_id=None if normalized_site_id in ("", "all") else normalized_site_id,
            department_id=None if normalized_department_id in ("", "all") else normalized_department_id,
            manager_user_id=None if normalized_manager_id in ("", "all") else normalized_manager_id,
            start_date_from=optional_date(start_date_from),
            start_date_to=optional_date(start_date_to),
            end_date_from=optional_date(end_date_from),
            end_date_to=optional_date(end_date_to),
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        department_lookup = self._department_lookup()
        return ProjectCatalogPageDesktopDto(
            items=tuple(
                serialize_project(
                    item.project,
                    site_lookup={str(item.project.site_id or ""): item.site_label},
                    department_lookup=department_lookup,
                    financial_currency_code=item.financial_currency_code,
                    approved_budget=item.approved_budget,
                    approved_budget_currency=getattr(
                        item,
                        "approved_budget_currency",
                        item.financial_currency_code,
                    ),
                    approved_budget_visible=bool(
                        getattr(
                            item,
                            "approved_budget_visible",
                            item.approved_budget is not None,
                        )
                    ),
                    client_label=item.client_label,
                )
                for item in result.items
            ),
            filtered_total=result.filtered_total,
            total=result.summary.total,
            active=result.summary.active,
            planned=result.summary.planned,
            on_hold=result.summary.on_hold,
            completed=result.summary.completed,
            page=result.page,
            page_size=result.page_size,
            sort_key=result.sort.key,
            sort_direction=result.sort.direction.value,
            approved_budget_visible=bool(
                getattr(
                    result,
                    "approved_budget_visible",
                    any(
                        bool(
                            getattr(
                                item,
                                "approved_budget_visible",
                                item.approved_budget is not None,
                            )
                        )
                        for item in result.items
                    ),
                )
            ),
        )

    def get_project(self, project_id: str) -> ProjectDesktopDto | None:
        normalized_id = str(project_id or "").strip()
        if not normalized_id or self._project_service is None:
            return None
        query_detail = getattr(self._project_service, "query_project_detail", None)
        if callable(query_detail):
            item = query_detail(normalized_id)
            if item is None:
                return None
            return serialize_project(
                item.project,
                site_lookup={str(item.project.site_id or ""): item.site_label},
                department_lookup=self._department_lookup(),
                financial_currency_code=item.financial_currency_code,
                approved_budget=item.approved_budget,
                approved_budget_currency=item.approved_budget_currency,
                approved_budget_visible=item.approved_budget_visible,
                client_label=item.client_label,
            )
        project = self._project_service.get_project(normalized_id)
        if project is None:
            return None
        return serialize_project(
            project,
            site_lookup=self._site_lookup(),
            department_lookup=self._department_lookup(),
        )

    def list_projects_by_status(self, status: str) -> tuple[ProjectDesktopDto, ...]:
        if self._project_service is None:
            return ()
        site_lookup = self._site_lookup()
        department_lookup = self._department_lookup()
        projects = sorted(
            self._project_service.list_projects_by_status(coerce_project_status(status)),
            key=lambda p: (p.name or "").casefold(),
        )
        return tuple(
            serialize_project(p, site_lookup=site_lookup, department_lookup=department_lookup)
            for p in projects
        )

    def search_projects(self, query: str) -> tuple[ProjectDesktopDto, ...]:
        if self._project_service is None or not query:
            return ()
        site_lookup = self._site_lookup()
        department_lookup = self._department_lookup()
        projects = sorted(
            self._project_service.search_projects_by_name(query),
            key=lambda p: (p.name or "").casefold(),
        )
        return tuple(
            serialize_project(p, site_lookup=site_lookup, department_lookup=department_lookup)
            for p in projects
        )

    def create_project(self, command: ProjectCreateCommand) -> ProjectDesktopDto:
        service = self._require_project_service()
        project = service.create_project(
            name=command.name,
            code=command.code,
            description=command.description,
            status=coerce_project_status(command.status),
            client_name=command.client_name,
            client_contact=command.client_contact,
            financial_currency_code=command.financial_currency_code,
            start_date=command.start_date,
            end_date=command.end_date,
            organization_id=command.organization_id,
            site_id=command.site_id,
            department_id=command.department_id,
            client_party_id=command.client_party_id,
            manager_user_id=command.manager_user_id,
        )
        return serialize_project(
            project,
            site_lookup=self._site_lookup(),
            department_lookup=self._department_lookup(),
        )

    def update_project(self, command: ProjectUpdateCommand) -> ProjectDesktopDto:
        service = self._require_project_service()
        project = service.update_project(
            command.project_id,
            expected_version=command.expected_version,
            name=command.name,
            code=command.code,
            description=command.description,
            status=coerce_project_status(command.status),
            start_date=command.start_date,
            end_date=command.end_date,
            client_name=command.client_name,
            client_contact=command.client_contact,
            organization_id=command.organization_id,
            site_id=command.site_id,
            department_id=command.department_id,
            client_party_id=command.client_party_id,
            manager_user_id=command.manager_user_id,
        )
        return serialize_project(
            project,
            site_lookup=self._site_lookup(),
            department_lookup=self._department_lookup(),
        )

    def set_project_status(self, project_id: str, status: str) -> ProjectDesktopDto:
        service = self._require_project_service()
        service.set_status(project_id, coerce_project_status(status))
        project = service.get_project(project_id)
        if project is None:
            raise RuntimeError("Project status updated but the project could not be reloaded.")
        return serialize_project(
            project,
            site_lookup=self._site_lookup(),
            department_lookup=self._department_lookup(),
        )

    def delete_project(self, project_id: str) -> None:
        self._require_project_service().delete_project(project_id)

    # ── Project resources ─────────────────────────────────────────────────────

    def list_project_resources(self, project_id: str) -> tuple[ProjectResourceDesktopDto, ...]:
        normalized_id = str(project_id or "").strip()
        if not normalized_id or self._project_resource_service is None:
            return ()
        list_by_project = getattr(
            self._project_resource_service,
            "list_for_project_workspace",
            None,
        )
        if not callable(list_by_project):
            return ()
        project_resources = list(list_by_project(normalized_id))

        resource_ids = tuple(str(getattr(pr, "resource_id", "") or "") for pr in project_resources)
        resources_by_id = resource_lookup(
            normalized_id, resource_ids,
            resource_service=self._resource_service,
        )
        rows = [
            serialize_project_resource(
                pr,
                resource_by_id=resources_by_id.get(str(getattr(pr, "resource_id", "") or "")),
            )
            for pr in project_resources
        ]
        return tuple(sorted(rows, key=lambda r: (not r.is_active, r.resource_name.casefold())))

    def list_project_resources_page(
        self, project_id: str, *, search_text: str = "", active: bool | None = None,
        page: int = 1, page_size: int = 25, sort_key: str = "resourceName",
        sort_direction: str = "asc",
    ) -> ProjectResourceDetailPageDesktopDto:
        result = self._require_project_service().query_project_resources_page(
            project_id, search_text=search_text, active=active, page=page,
            page_size=page_size, sort_key=sort_key, sort_direction=sort_direction)
        return ProjectResourceDetailPageDesktopDto(
            items=tuple(ProjectResourceDetailDesktopDto(
                id=item.project_resource_id, resource_id=item.resource_id,
                resource_code=item.resource_code, resource_name=item.resource_name,
                role=item.role, planned_hours=str(item.planned_hours),
                allocated_hours=str(item.allocated_hours), actual_hours=str(item.actual_hours),
                remaining_hours=str(item.remaining_hours), is_active=item.is_active,
                version=item.version,
            ) for item in result.items), filtered_total=result.filtered_total,
            page=result.page, page_size=result.page_size, sort_key=result.sort.key,
            sort_direction=result.sort.direction.value)

    def list_project_activity_page(
        self, project_id: str, *, search_text: str = "", category: str = "all",
        page: int = 1, page_size: int = 25,
    ) -> DetailActivityPageDesktopDto:
        result = self._require_project_service().query_project_activity_page(
            project_id, search_text=search_text, category=category,
            page=page, page_size=page_size)
        return DetailActivityPageDesktopDto(
            items=tuple(DetailActivityDesktopDto(
                id=item.activity_id, occurred_at=item.occurred_at.isoformat(),
                actor_id=item.actor_id, action=item.action, entity_type=item.entity_type,
                summary=item.summary, details=item.details,
            ) for item in result.items), filtered_total=result.filtered_total,
            page=result.page, page_size=result.page_size)

    def list_assignable_resources(self, project_id: str) -> tuple[ProjectAssignableResourceOptionDescriptor, ...]:
        normalized_id = str(project_id or "").strip()
        if not normalized_id:
            return ()
        assigned_ids = {row.resource_id for row in self.list_project_resources(normalized_id)}
        return build_assignable_options(
            normalized_id, assigned_ids,
            resource_service=self._resource_service,
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
            planned_hours=max(Decimal("0"), command.planned_hours),
            is_active=command.is_active,
            expected_version=command.expected_version,
        )

    def get_project_resource_usage(self, project_resource_id: str) -> ProjectResourceUsageDesktopDto | None:
        normalized_id = str(project_resource_id or "").strip()
        if not normalized_id or self._project_resource_service is None:
            return None
        get_usage = getattr(self._project_resource_service, "get_usage", None)
        if not callable(get_usage):
            return None
        fact = get_usage(normalized_id)
        return serialize_project_resource_usage(fact)

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

    def _department_lookup(self) -> dict[str, str]:
        if self._department_service is None:
            return {}
        try:
            return {
                str(department.id): str(getattr(department, "name", "") or "").strip()
                for department in self._department_service.list_departments(active_only=None)
                if getattr(department, "id", None)
            }
        except Exception:
            return {}

__all__ = ["ProjectManagementProjectsDesktopApi"]
