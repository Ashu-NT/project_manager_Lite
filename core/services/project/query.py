from __future__ import annotations

from typing import List

from core.interfaces import ProjectRepository
from core.models import Project, ProjectStatus
from core.services.auth.authorization import require_permission


class ProjectQueryMixin:
    _project_repo: ProjectRepository

    def list_projects(self) -> List[Project]:
        require_permission(self._user_session, "project.read", operation_label="list projects")
        return self._project_repo.list_all()

    def get_project(self, project_id: str) -> Project | None:
        require_permission(self._user_session, "project.read", operation_label="view project")
        return self._project_repo.get(project_id)

    def list_projects_by_status(self, status: ProjectStatus) -> List[Project]:
        require_permission(self._user_session, "project.read", operation_label="list projects by status")
        return [project for project in self._project_repo.list_all() if project.status == status]

    def search_projects_by_name(self, query: str) -> List[Project]:
        require_permission(self._user_session, "project.read", operation_label="search projects")
        normalized = query.strip().lower()
        return [project for project in self._project_repo.list_all() if normalized in project.name.lower()]


__all__ = ["ProjectQueryMixin"]
