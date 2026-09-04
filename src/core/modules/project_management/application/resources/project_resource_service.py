from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.resources.commands.project_resource_commands import (
    ProjectResourceCommandMixin,
)
from src.core.modules.project_management.application.resources.queries.project_resource_queries import (
    ProjectResourceQueryMixin,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.resources.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin


class ProjectResourceService(
    ProjectManagementModuleGuardMixin,
    ProjectResourceCommandMixin,
    ProjectResourceQueryMixin,
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
        transactional_dispatcher=None,
        post_commit_bus=None,
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
        self._transactional_dispatcher = transactional_dispatcher
        self._post_commit_bus = post_commit_bus


__all__ = ["ProjectResourceService"]
