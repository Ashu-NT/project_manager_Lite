from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.core.modules.project_management.access.scope_permissions import (
    filter_project_rows,
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.common.pagination import (
    PageRequest,
    normalize_page_for_total,
)
from src.core.modules.project_management.application.projects.dto.responses.project import (
    ProjectResponse,
)
from src.core.modules.project_management.application.projects.mappers.project import (
    map_project_response,
)
from src.core.modules.project_management.contracts.reads import ReadSort
from src.core.modules.project_management.contracts.reads.projects import (
    ProjectActivityPage,
    ProjectCatalogReader,
    ProjectCatalogReadItem,
    ProjectCatalogReadPage,
    ProjectManagerCandidateFact,
    ProjectResourceDetailPage,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import ConfigurationError
from src.core.platform.domain.security.auth.session import UserSessionContext


class ProjectQueryHandler(ProjectManagementModuleGuardMixin):
    def __init__(
        self,
        *,
        project_repo: ProjectRepository,
        project_catalog_reader: ProjectCatalogReader | None,
        tenant_context_service: TenantContextService | None,
        user_session: UserSessionContext | None,
        module_catalog_service=None,
    ) -> None:
        self._project_repo = project_repo
        self._project_catalog_reader = project_catalog_reader
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def list_eligible_manager_candidates(self) -> tuple[ProjectManagerCandidateFact, ...]:
        require_permission(
            self._user_session, "project.read", operation_label="list project managers"
        )
        if self._project_catalog_reader is None or self._tenant_context_service is None:
            raise ConfigurationError("Project catalog reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="list project managers"
        )
        return self._project_catalog_reader.list_eligible_manager_candidates(
            tenant_id=scope.tenant_id, organization_id=scope.organization_id
        )

    def list_projects(self) -> list[ProjectResponse]:
        require_permission(self._user_session, "project.read", operation_label="list projects")
        project_rows = self._project_repo.list()
        visible = filter_project_rows(
            project_rows,
            self._user_session,
            permission_code="project.read",
            project_id_getter=lambda project: project.id,
        )
        return [map_project_response(project) for project in visible]

    def query_catalog_page(
        self,
        *,
        search_text: str = "",
        status: ProjectStatus | None = None,
        project_name: str | None = None,
        client_name: str | None = None,
        site_id: str | None = None,
        department_id: str | None = None,
        manager_user_id: str | None = None,
        start_date_from: date | None = None,
        start_date_to: date | None = None,
        end_date_from: date | None = None,
        end_date_to: date | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "title",
        sort_direction: str = "asc",
    ) -> ProjectCatalogReadPage:
        require_permission(
            self._user_session,
            "project.read",
            operation_label="list project catalog",
        )
        if self._project_catalog_reader is None or self._tenant_context_service is None:
            raise ConfigurationError("Project catalog reader is not configured.")
        reader = self._project_catalog_reader
        page_request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys={
                "title",
                "projectCode",
                "statusLabel",
                "clientLabel",
                "siteLabel",
                "clientContact",
                "startDateLabel",
                "endDateLabel",
                "approvedBudgetLabel",
            },
            default_key="title",
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="list project catalog"
        )
        allowed_project_ids: tuple[str, ...] | None = None
        if self._user_session is not None and self._user_session.is_project_restricted():
            allowed_project_ids = tuple(
                sorted(self._user_session.project_ids_for("project.read"))
            )
        finance_allowed_project_ids = self._finance_allowed_project_ids()
        def read_page(page_number: int) -> ProjectCatalogReadPage:
            return reader.read_page(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                allowed_project_ids=allowed_project_ids,
                finance_allowed_project_ids=finance_allowed_project_ids,
                search_text=str(search_text or "").strip(),
                status=status,
                project_name=project_name,
                client_name=client_name,
                site_id=site_id,
                department_id=department_id,
                manager_user_id=manager_user_id,
                start_date_from=start_date_from,
                start_date_to=start_date_to,
                end_date_from=end_date_from,
                end_date_to=end_date_to,
                page=page_number,
                page_size=page_request.page_size,
                sort=sort,
            )

        result = read_page(page_request.page)
        normalized_page = normalize_page_for_total(
            page=result.page,
            page_size=result.page_size,
            total=result.filtered_total,
        )
        if normalized_page != result.page:
            result = read_page(normalized_page)
        return replace(
            result,
            approved_budget_visible=self._can_read_any_project_finance(),
        )

    def query_project_detail(self, project_id: str) -> ProjectCatalogReadItem | None:
        require_permission(self._user_session, "project.read", operation_label="view project")
        normalized_project_id = str(project_id or "").strip()
        if not normalized_project_id:
            return None
        require_project_permission(
            self._user_session,
            normalized_project_id,
            "project.read",
            operation_label="view project",
        )
        if self._project_catalog_reader is None or self._tenant_context_service is None:
            raise ConfigurationError("Project catalog reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project"
        )
        can_read_finance = bool(
            self._user_session is not None
            and self._user_session.has_project_permission(
                normalized_project_id, "finance.read"
            )
        )
        result = self._project_catalog_reader.read_one(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=normalized_project_id,
            include_approved_budget=can_read_finance,
        )
        return result

    def query_project_resources_page(
        self, project_id: str, *, search_text: str = "", active: bool | None = None,
        page: int = 1, page_size: int = 25, sort_key: str = "resourceName",
        sort_direction: str = "asc",
    ) -> ProjectResourceDetailPage:
        normalized_id = str(project_id or "").strip()
        require_project_permission(self._user_session, normalized_id, "project.read",
                                   operation_label="view project resources")
        if self._project_catalog_reader is None or self._tenant_context_service is None:
            raise ConfigurationError("Project catalog reader is not configured.")
        reader = self._project_catalog_reader
        request = PageRequest(page=page, page_size=page_size)
        sort = ReadSort.normalize(
            key=sort_key, direction=sort_direction,
            allowed_keys={"resourceName", "resourceCode", "role", "plannedHours",
                          "allocatedHours", "actualHours", "remainingHours"},
            default_key="resourceName",
        )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project resources")
        def read_page(page_number: int) -> ProjectResourceDetailPage:
            return reader.read_resources_page(
                tenant_id=scope.tenant_id, organization_id=scope.organization_id,
                project_id=normalized_id, search_text=str(search_text or "").strip(),
                active=active, page=page_number, page_size=request.page_size, sort=sort,
            )

        result = read_page(request.page)
        normalized_page = normalize_page_for_total(page=result.page, page_size=result.page_size,
                                                   total=result.filtered_total)
        if normalized_page != result.page:
            result = read_page(normalized_page)
        return result

    def query_project_activity_page(
        self, project_id: str, *, search_text: str = "", category: str = "all",
        page: int = 1, page_size: int = 25,
    ) -> ProjectActivityPage:
        normalized_id = str(project_id or "").strip()
        require_project_permission(self._user_session, normalized_id, "project.read",
                                   operation_label="view project activity")
        if self._project_catalog_reader is None or self._tenant_context_service is None:
            raise ConfigurationError("Project catalog reader is not configured.")
        reader = self._project_catalog_reader
        request = PageRequest(page=page, page_size=page_size)
        normalized_category = str(category or "all").strip().lower()
        if normalized_category not in {"all", "project", "resources"}:
            normalized_category = "all"
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project activity")
        def read_page(page_number: int) -> ProjectActivityPage:
            return reader.read_activity_page(
                tenant_id=scope.tenant_id, organization_id=scope.organization_id,
                project_id=normalized_id, search_text=str(search_text or "").strip(),
                category=normalized_category, page=page_number,
                page_size=request.page_size,
            )

        result = read_page(request.page)
        normalized_page = normalize_page_for_total(page=result.page, page_size=result.page_size,
                                                   total=result.filtered_total)
        if normalized_page != result.page:
            result = read_page(normalized_page)
        return result

    def _finance_allowed_project_ids(self) -> tuple[str, ...] | None:
        if self._user_session is None or not self._user_session.has_permission("finance.read"):
            return ()
        if self._user_session.is_project_restricted():
            return tuple(sorted(self._user_session.project_ids_for("finance.read")))
        return None

    def _can_read_any_project_finance(self) -> bool:
        return bool(
            self._user_session is not None
            and self._user_session.has_any_project_access("finance.read")
        )

    def list_for_task_workspace(self) -> list[ProjectResponse]:
        permission_codes = ("project.read", "task.read", "task.manage")
        require_any_permission(
            self._user_session,
            permission_codes,
            operation_label="list task projects",
        )
        projects = self._project_repo.list()
        visible_project_ids = {
            project.id
            for permission_code in permission_codes
            for project in filter_project_rows(
                projects,
                self._user_session,
                permission_code=permission_code,
                project_id_getter=lambda row: row.id,
            )
        }
        return [map_project_response(project) for project in projects if project.id in visible_project_ids]

    def get_project(self, project_id: str) -> ProjectResponse | None:
        require_permission(self._user_session, "project.read", operation_label="view project")
        project = self._project_repo.get(project_id)
        if project is None:
            return None
        require_project_permission(
            self._user_session,
            project_id,
            "project.read",
            operation_label="view project",
        )
        return map_project_response(project)

    def list_projects_by_status(self, status: ProjectStatus) -> list[ProjectResponse]:
        require_permission(self._user_session, "project.read", operation_label="list projects by status")
        return [project for project in self.list_projects() if project.status == status]

    def search_projects_by_name(self, query: str) -> list[ProjectResponse]:
        require_permission(self._user_session, "project.read", operation_label="search projects")
        normalized = query.strip().lower()
        return [project for project in self.list_projects() if normalized in project.name.lower()]


__all__ = ["ProjectQueryHandler"]
