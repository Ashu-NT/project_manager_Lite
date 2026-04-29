from __future__ import annotations

from src.core.modules.project_management.contracts.repositories.project import ProjectResourceRepository
from src.core.modules.project_management.domain.projects.project import ProjectResource
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.auth.authorization import require_permission


class ProjectResourceQueryMixin:
    _project_resource_repo: ProjectResourceRepository

    def list_by_project(self, project_id: str) -> list[ProjectResource]:
        require_permission(
            self._user_session,
            "project.read",
            operation_label="list project resources",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "project.read",
            operation_label="list project resources",
        )
        return self._project_resource_repo.list_by_project(project_id)

    def get(self, project_resource_id: str) -> ProjectResource | None:
        require_permission(
            self._user_session,
            "project.read",
            operation_label="view project resource",
        )
        row = self._project_resource_repo.get(project_resource_id)
        if row is None:
            return None
        require_project_permission(
            self._user_session,
            row.project_id,
            "project.read",
            operation_label="view project resource",
        )
        return row

    def get_for_project(self, project_id: str, resource_id: str) -> ProjectResource | None:
        require_permission(
            self._user_session,
            "project.read",
            operation_label="view project resource membership",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "project.read",
            operation_label="view project resource membership",
        )
        return self._project_resource_repo.get_for_project(project_id, resource_id)


__all__ = ["ProjectResourceQueryMixin"]
