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
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.resources.resource import (
    ResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.projects.project import ProjectResource
from src.core.shared.persistence.unit_of_work import UnitOfWorkFactory


class ProjectResourceService(ProjectManagementModuleGuardMixin):
    """Project-resource membership application service orchestrator."""

    def __init__(
        self,
        project_resource_repo: ProjectResourceRepository,
        resource_repo: ResourceRepository,
        project_repo: ProjectRepository,
        user_session=None,
        activity_service=None,
        module_catalog_service=None,
        tenant_context_service=None,
        task_repo: TaskRepository | None = None,
        assignment_repo: AssignmentRepository | None = None,
        financial_profile_repo: ProjectFinancialProfileRepository | None = None,
        shared_uow_factory: UnitOfWorkFactory | None = None,
    ):
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        self._command = ProjectResourceCommandHandler(
            project_resource_repo=project_resource_repo,
            resource_repo=resource_repo,
            project_repo=project_repo,
            user_session=user_session,
            activity_service=activity_service,
            tenant_context_service=tenant_context_service,
            task_repo=task_repo,
            assignment_repo=assignment_repo,
            financial_profile_repo=financial_profile_repo,
            shared_uow_factory=shared_uow_factory,
        )
        self._query = ProjectResourceQueryHandler(
            project_resource_repo=project_resource_repo,
            task_repo=task_repo,
            assignment_repo=assignment_repo,
            user_session=user_session,
        )

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
