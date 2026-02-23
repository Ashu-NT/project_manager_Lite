from __future__ import annotations

from typing import List

from core.models import Project, ProjectStatus


class ProjectQueryMixin:
    def list_projects(self) -> List[Project]:
        return self._project_repo.list_all()

    def get_project(self, project_id: str) -> Project | None:
        return self._project_repo.get(project_id)

    def list_projects_by_status(self, status: ProjectStatus) -> List[Project]:
        return [project for project in self._project_repo.list_all() if project.status == status]

    def search_projects_by_name(self, query: str) -> List[Project]:
        normalized = query.strip().lower()
        return [project for project in self._project_repo.list_all() if normalized in project.name.lower()]


__all__ = ["ProjectQueryMixin"]
