from __future__ import annotations

from decimal import Decimal

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.resources.commands.project_resource_commands import (
    ProjectResourceCommandHandler,
)
from src.core.modules.project_management.application.resources.queries.project_resource_queries import (
    ProjectResourceQueryHandler,
)
from src.core.modules.project_management.contracts.reads.projects.models import (
    ProjectResourceUsageFact,
)
from src.core.modules.project_management.domain.projects.project import ProjectResource


class ProjectResourceService(ProjectManagementModuleGuardMixin):
    """Project-resource membership application service orchestrator."""

    def __init__(
        self,
        command_handler: ProjectResourceCommandHandler,
        query_handler: ProjectResourceQueryHandler,
        user_session=None,
        module_catalog_service=None,
    ):
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        self._command = command_handler
        self._query = query_handler

    def add_to_project(
        self,
        project_id: str,
        resource_id: str,
        hourly_rate: Decimal | int | str | None = None,
        currency_code: str | None = None,
        planned_hours: Decimal | int | str = Decimal(0),
        is_active: bool = True,
    ) -> ProjectResource:
        return self._command.add_to_project(
            project_id,
            resource_id,
            hourly_rate,
            currency_code,
            planned_hours,
            is_active,
        )

    def update(
        self,
        pr_id: str,
        hourly_rate: Decimal | int | str | None,
        currency_code: str | None,
        planned_hours: Decimal | int | str,
        is_active: bool,
        *,
        expected_version: int | None = None,
    ) -> None:
        self._command.update(
            pr_id,
            hourly_rate,
            currency_code,
            planned_hours,
            is_active,
            expected_version=expected_version,
        )

    def set_active(self, pr_id: str, is_active: bool) -> None:
        self._command.set_active(pr_id, is_active)

    def delete(self, pr_id: str) -> None:
        self._command.delete(pr_id)

    def list_by_project(self, project_id: str) -> list[ProjectResource]:
        return self._query.list_by_project(project_id)

    def list_for_project_workspace(self, project_id: str) -> list[ProjectResource]:
        return self._query.list_for_project_workspace(project_id)

    def list_for_task_workspace(self, project_id: str) -> list[ProjectResource]:
        return self._query.list_for_task_workspace(project_id)

    def get(self, project_resource_id: str) -> ProjectResource | None:
        return self._query.get(project_resource_id)

    def get_usage(self, project_resource_id: str) -> ProjectResourceUsageFact:
        return self._query.get_usage(project_resource_id)

    def get_for_project(self, project_id: str, resource_id: str) -> ProjectResource | None:
        return self._query.get_for_project(project_id, resource_id)


__all__ = ["ProjectResourceService"]
