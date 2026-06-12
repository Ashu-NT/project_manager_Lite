from __future__ import annotations


from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.domain.projects.project import Project
from src.core.platform.access.authorization import filter_project_rows, require_project_permission
from src.core.platform.auth.authorization import require_permission
from src.core.modules.project_management.domain.enums import ProjectStatus


class ProjectQueryMixin:
    _project_repo: ProjectRepository

    def list_projects(self) -> list[Project]:
        require_permission(self._user_session, "project.read", operation_label="list projects")
        organization_id = self._active_organization_id(operation_label="list projects")
        project_rows = self._project_repo.list_for_organization(organization_id)
        return filter_project_rows(
            project_rows,
            self._user_session,
            permission_code="project.read",
            project_id_getter=lambda project: project.id,
        )

    def get_project(self, project_id: str) -> Project | None:
        require_permission(self._user_session, "project.read", operation_label="view project")
        project = self._project_repo.get(project_id)
        if project is None:
            return None
        if not self._is_project_in_active_organization(project):
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

    def _active_organization_id(self, *, operation_label: str) -> str | None:
        tenant_context = getattr(self, "_tenant_context_service", None)
        if tenant_context is None:
            from src.core.platform.common.exceptions import BusinessRuleError
            raise BusinessRuleError(
                f"Active organization context is required for {operation_label}.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return tenant_context.require_active_organization_id(operation_label=operation_label)

    def _is_project_in_active_organization(self, project: Project) -> bool:
        organization_id = self._active_organization_id(operation_label="view project")
        project_organization_id = str(getattr(project, "organization_id", "") or "").strip()
        return bool(project_organization_id and project_organization_id == organization_id)


__all__ = ["ProjectQueryMixin"]
