from __future__ import annotations

from dataclasses import replace
from datetime import date

from src.core.modules.project_management.access.scope_permissions import (
    filter_project_rows,
    require_project_permission,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.application.common.pagination import (
    PageRequest,
    normalize_page_for_total,
)
from src.core.modules.project_management.contracts.reads.projects import (
    ProjectCatalogReadPage,
    ProjectCatalogReader,
)
from src.core.modules.project_management.contracts.reads import ReadSort
from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.modules.project_management.domain.projects.project import Project
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_any_permission,
    require_permission,
)


class ProjectQueryMixin:
    _project_repo: ProjectRepository
    _project_catalog_reader: ProjectCatalogReader | None

    def list_projects(self) -> list[Project]:
        require_permission(self._user_session, "project.read", operation_label="list projects")
        project_rows = self._project_repo.list()
        return filter_project_rows(
            project_rows,
            self._user_session,
            permission_code="project.read",
            project_id_getter=lambda project: project.id,
        )

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
            raise RuntimeError("Project catalog reader is not configured.")
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
        read_kwargs = dict(
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
            page=page_request.page,
            page_size=page_request.page_size,
            sort=sort,
        )
        result = self._project_catalog_reader.read_page(**read_kwargs)
        normalized_page = normalize_page_for_total(
            page=result.page,
            page_size=result.page_size,
            total=result.filtered_total,
        )
        if normalized_page != result.page:
            read_kwargs["page"] = normalized_page
            result = self._project_catalog_reader.read_page(**read_kwargs)
        return replace(
            result,
            approved_budget_visible=self._can_read_any_project_finance(),
        )

    def query_project_detail(self, project_id: str):
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
            raise RuntimeError("Project catalog reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view project"
        )
        can_read_finance = bool(
            self._user_session is not None
            and self._user_session.has_project_permission(
                normalized_project_id, "finance.read"
            )
        )
        return self._project_catalog_reader.read_one(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=normalized_project_id,
            include_approved_budget=can_read_finance,
        )

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

    def list_for_task_workspace(self) -> list[Project]:
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
        return [project for project in projects if project.id in visible_project_ids]

    def get_project(self, project_id: str) -> Project | None:
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
        return project

    def list_projects_by_status(self, status: ProjectStatus) -> list[Project]:
        require_permission(self._user_session, "project.read", operation_label="list projects by status")
        return [project for project in self.list_projects() if project.status == status]

    def search_projects_by_name(self, query: str) -> list[Project]:
        require_permission(self._user_session, "project.read", operation_label="search projects")
        normalized = query.strip().lower()
        return [project for project in self.list_projects() if normalized in project.name.lower()]


__all__ = ["ProjectQueryMixin"]
