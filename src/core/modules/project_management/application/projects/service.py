from __future__ import annotations

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.projects.commands.create import (
    ProjectCreateHandler,
)
from src.core.modules.project_management.application.projects.commands.deletion import (
    ProjectDeletionHandler,
)
from src.core.modules.project_management.application.projects.commands.status import (
    ProjectStatusHandler,
)
from src.core.modules.project_management.application.projects.commands.update import (
    ProjectUpdateHandler,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
from src.core.platform.domain.security.auth.session import UserSessionContext


class ProjectService(ProjectManagementModuleGuardMixin):
    """Project application service orchestrator."""

    def __init__(
        self,
        *,
        query_handler: ProjectQueryHandler,
        status_handler: ProjectStatusHandler,
        deletion_handler: ProjectDeletionHandler,
        create_handler: ProjectCreateHandler,
        update_handler: ProjectUpdateHandler,
        module_catalog_service=None,
        user_session: UserSessionContext | None = None,
    ):
        self._module_catalog_service = module_catalog_service
        self._user_session = user_session
        self._query_handler = query_handler
        self._status_handler = status_handler
        self._deletion_handler = deletion_handler
        self._create_handler = create_handler
        self._update_handler = update_handler

    def update_project(self, *args, **kwargs):
        return self._update_handler.update_project(*args, **kwargs)

    def update_dates_from_tasks(self, project_id: str) -> None:
        self._update_handler.update_dates_from_tasks(project_id)

    def create_project(self, *args, **kwargs):
        return self._create_handler.create_project(*args, **kwargs)

    def delete_project(self, project_id: str) -> None:
        self._deletion_handler.delete_project(project_id)

    def set_status(self, project_id, status, *, expected_version=None):
        return self._status_handler.set_status(
            project_id, status, expected_version=expected_version
        )

    def bulk_set_status(self, project_ids, status):
        return self._status_handler.bulk_set_status(project_ids, status)

    def list_eligible_manager_candidates(self):
        return self._query_handler.list_eligible_manager_candidates()

    def list_projects(self):
        return self._query_handler.list_projects()

    def query_catalog_page(self, **kwargs):
        return self._query_handler.query_catalog_page(**kwargs)

    def query_project_detail(self, project_id: str):
        return self._query_handler.query_project_detail(project_id)

    def query_project_resources_page(self, project_id: str, **kwargs):
        return self._query_handler.query_project_resources_page(project_id, **kwargs)

    def query_project_activity_page(self, project_id: str, **kwargs):
        return self._query_handler.query_project_activity_page(project_id, **kwargs)

    def list_for_task_workspace(self):
        return self._query_handler.list_for_task_workspace()

    def get_project(self, project_id: str):
        return self._query_handler.get_project(project_id)

    def list_projects_by_status(self, status):
        return self._query_handler.list_projects_by_status(status)

    def search_projects_by_name(self, query: str):
        return self._query_handler.search_projects_by_name(query)

__all__ = ["ProjectService"]
