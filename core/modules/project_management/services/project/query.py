from __future__ import annotations

from typing import List

from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.domain.projects.project import Project
from core.modules.project_management.domain.enums import ProjectStatus
from src.core.platform.access.authorization import filter_project_rows, require_project_permission
from src.core.platform.auth.authorization import require_permission


class ProjectQueryMixin:
    _project_repo: ProjectRepository

    def list_projects(self) -> List[Project]:
        require_permission(self._user_session, "project.read", operation_label="list projects")
        return filter_project_rows(
            self._project_repo.list_all(),
            self._user_session,
            permission_code="project.read",
            project_id_getter=lambda project: project.id,
        )

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

    def list_projects_by_status(self, status: ProjectStatus) -> List[Project]:
        require_permission(self._user_session, "project.read", operation_label="list projects by status")
        return [project for project in self.list_projects() if project.status == status]

    def search_projects_by_name(self, query: str) -> List[Project]:
        require_permission(self._user_session, "project.read", operation_label="search projects")
        normalized = query.strip().lower()
        return [project for project in self.list_projects() if normalized in project.name.lower()]


__all__ = ["ProjectQueryMixin"]
