from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.resources.commands.project_resource_commands import (
    ProjectResourceCommandMixin,
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


class ProjectResourceService(
    ProjectManagementModuleGuardMixin,
    ProjectResourceCommandMixin,
):
    """Project-resource membership application service orchestrator."""

    def __init__(
        self,
        project_resource_repo: ProjectResourceRepository,
        resource_repo: ResourceRepository,
        project_repo: ProjectRepository,
        session: Session,
        user_session=None,
        activity_service=None,
        module_catalog_service=None,
        tenant_context_service=None,
        task_repo: TaskRepository | None = None,
        assignment_repo: AssignmentRepository | None = None,
        financial_profile_repo: ProjectFinancialProfileRepository | None = None,
        shared_uow_factory: UnitOfWorkFactory | None = None,
    ):
        self._project_resource_repo: ProjectResourceRepository = project_resource_repo
        self._resource_repo: ResourceRepository = resource_repo
        self._project_repo: ProjectRepository = project_repo
        self._session: Session = session
        self._user_session = user_session
        self._activity_service = activity_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        # Only needed for the envelope-shrink guard in
        # ProjectResourceCommandMixin.update() — see its docstring.
        self._task_repo: TaskRepository | None = task_repo
        self._assignment_repo: AssignmentRepository | None = assignment_repo
        self._financial_profile_repo = financial_profile_repo
        self._shared_uow_factory = shared_uow_factory
        self._query = ProjectResourceQueryHandler(
            project_resource_repo=project_resource_repo,
            task_repo=task_repo,
            assignment_repo=assignment_repo,
            user_session=user_session,
        )

    def _require_shared_uow_factory(self) -> UnitOfWorkFactory:
        if self._shared_uow_factory is None:
            raise RuntimeError("Project resource write transaction factory is not configured.")
        return self._shared_uow_factory

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
