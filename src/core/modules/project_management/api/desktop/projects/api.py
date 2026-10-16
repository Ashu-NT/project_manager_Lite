"""ProjectManagementProjectsDesktopApi — thin projects desktop facade."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.projects.utils.project_utils import (
    coerce_project_status,
    optional_date,
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
from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
    ProjectUpdateCommand,
)
from src.core.modules.project_management.application.projects.dto.commands.project_resources import (
    ProjectResourceAssignCommand,
    ProjectResourceUpdateCommand,
)
from src.core.modules.project_management.application.projects.dto.responses.project import (
    ProjectResponse,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
from src.core.modules.project_management.application.resources import (
    ProjectResourceCommandHandler,
    ProjectResourceQueryHandler,
    ResourceQueryHandler,
)
from src.core.modules.project_management.application.resources.dto.responses.catalog import (
    ResourceResponse,
)
from src.core.modules.project_management.application.resources.dto.responses.project_resources import (
    ProjectResourceResponse,
)
from src.core.modules.project_management.contracts.reads.projects.models import (
    ProjectActivityPage,
    ProjectCatalogReadItem,
    ProjectCatalogReadPage,
    ProjectManagerCandidateFact,
    ProjectResourceDetailPage,
    ProjectResourceUsageFact,
)
from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.platform.common.exceptions import (
    ConfigurationError,
)


class ProjectManagementProjectsDesktopApi:
    def __init__(
        self,
        *,
        project_create: ProjectCreateHandler | None = None,
        project_update: ProjectUpdateHandler | None = None,
        project_status: ProjectStatusHandler | None = None,
        project_deletion: ProjectDeletionHandler | None = None,
        project_query: ProjectQueryHandler | None = None,
        project_resource_query: ProjectResourceQueryHandler | None = None,
        project_resource_commands: ProjectResourceCommandHandler | None = None,
        resource_query: ResourceQueryHandler | None = None,
    ) -> None:
        self._project_create = project_create
        self._project_update = project_update
        self._project_status = project_status
        self._project_deletion = project_deletion
        self._project_query = project_query
        self._project_resource_query = project_resource_query
        self._project_resource_commands = project_resource_commands
        self._resource_service = resource_query

    # ── Status options ────────────────────────────────────────────────────────

    def list_statuses(self) -> tuple[ProjectStatus, ...]:
        return tuple(ProjectStatus)

    def list_manager_candidates(self) -> tuple[ProjectManagerCandidateFact, ...]:
        return tuple(self._require_project_query().list_eligible_manager_candidates())

    # ── Project CRUD ──────────────────────────────────────────────────────────

    def list_projects(self) -> tuple[ProjectResponse, ...]:
        if self._project_query is None:
            return ()
        return tuple(self._project_query.list_projects())

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
    ) -> ProjectCatalogReadPage:
        service = self._require_project_query()
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
            department_id=None
            if normalized_department_id in ("", "all")
            else normalized_department_id,
            manager_user_id=None
            if normalized_manager_id in ("", "all")
            else normalized_manager_id,
            start_date_from=optional_date(start_date_from),
            start_date_to=optional_date(start_date_to),
            end_date_from=optional_date(end_date_from),
            end_date_to=optional_date(end_date_to),
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return result

    def get_project(self, project_id: str) -> ProjectCatalogReadItem | None:
        normalized_id = str(project_id or "").strip()
        if not normalized_id or self._project_query is None:
            return None
        return self._project_query.query_project_detail(normalized_id)

    def list_projects_by_status(self, status: str) -> tuple[ProjectResponse, ...]:
        if self._project_query is None:
            return ()
        return tuple(
            self._project_query.list_projects_by_status(coerce_project_status(status))
        )

    def search_projects(self, query: str) -> tuple[ProjectResponse, ...]:
        if self._project_query is None or not query:
            return ()
        return tuple(self._project_query.search_projects_by_name(query))

    def create_project(self, command: ProjectCreateCommand) -> ProjectResponse:
        if self._project_create is None:
            raise ConfigurationError("Project creation is not connected.")
        return self._project_create.create_project(command)

    def update_project(self, command: ProjectUpdateCommand) -> ProjectResponse:
        if self._project_update is None:
            raise ConfigurationError("Project updates are not connected.")
        return self._project_update.update_project(command)

    def set_project_status(self, project_id: str, status: str) -> ProjectResponse:
        if self._project_status is None:
            raise ConfigurationError("Project status changes are not connected.")
        return self._project_status.set_status(
            project_id, coerce_project_status(status)
        )

    def bulk_set_project_status(
        self, project_ids: tuple[str, ...], status: str
    ) -> tuple[ProjectResponse, ...]:
        if self._project_status is None:
            raise ConfigurationError("Project status changes are not connected.")
        return tuple(
            self._project_status.bulk_set_status(
                project_ids, coerce_project_status(status)
            )
        )

    def delete_project(self, project_id: str) -> None:
        if self._project_deletion is None:
            raise ConfigurationError("Project deletion is not connected.")
        self._project_deletion.delete_project(project_id)

    # ── Project resources ─────────────────────────────────────────────────────

    def list_project_resources(
        self, project_id: str
    ) -> tuple[ProjectResourceResponse, ...]:
        normalized_id = str(project_id or "").strip()
        if not normalized_id or self._project_resource_query is None:
            return ()
        return tuple(
            self._project_resource_query.list_for_project_workspace(normalized_id)
        )

    def list_project_resources_page(
        self,
        project_id: str,
        *,
        search_text: str = "",
        active: bool | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "resourceName",
        sort_direction: str = "asc",
    ) -> ProjectResourceDetailPage:
        result = self._require_project_query().query_project_resources_page(
            project_id,
            search_text=search_text,
            active=active,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )
        return result

    def list_project_activity_page(
        self,
        project_id: str,
        *,
        search_text: str = "",
        category: str = "all",
        page: int = 1,
        page_size: int = 25,
    ) -> ProjectActivityPage:
        result = self._require_project_query().query_project_activity_page(
            project_id,
            search_text=search_text,
            category=category,
            page=page,
            page_size=page_size,
        )
        return result

    def list_resource_context(
        self, project_id: str, *, resource_ids: tuple[str, ...] = ()
    ) -> tuple[ResourceResponse, ...]:
        if self._resource_service is None:
            return ()
        return tuple(
            self._resource_service.list_for_project_workspace(
                project_id, resource_ids=resource_ids
            )
        )

    def list_assignable_resources(
        self, project_id: str
    ) -> tuple[ResourceResponse, ...]:
        normalized_id = str(project_id or "").strip()
        if not normalized_id:
            return ()
        assigned_ids = {
            row.resource_id for row in self.list_project_resources(normalized_id)
        }
        return tuple(
            row
            for row in self.list_resource_context(normalized_id)
            if row.is_active and row.id not in assigned_ids
        )

    def add_project_resource(
        self, command: ProjectResourceAssignCommand
    ) -> ProjectResourceResponse:
        return self._require_project_resource_commands().add_to_project(command)

    def update_project_resource(self, command: ProjectResourceUpdateCommand) -> None:
        self._require_project_resource_commands().update(command)

    def get_project_resource_usage(
        self, project_resource_id: str
    ) -> ProjectResourceUsageFact | None:
        normalized_id = str(project_resource_id or "").strip()
        if not normalized_id or self._project_resource_query is None:
            return None
        return self._project_resource_query.get_usage(normalized_id)

    def remove_project_resource(self, project_resource_id: str) -> None:
        self._require_project_resource_commands().delete(project_resource_id)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _require_project_query(self) -> ProjectQueryHandler:
        if self._project_query is None:
            raise ConfigurationError(
                "Project management projects query is not connected."
            )
        return self._project_query

    def _require_project_resource_commands(self) -> ProjectResourceCommandHandler:
        if self._project_resource_commands is None:
            raise ConfigurationError(
                "Project management project-resource desktop API is not connected."
            )
        return self._project_resource_commands


__all__ = ["ProjectManagementProjectsDesktopApi"]
