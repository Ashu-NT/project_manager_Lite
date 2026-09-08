from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.projects.project import ProjectRepository
from src.core.modules.project_management.contracts.reads.projects import ProjectCatalogReader
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.contracts.uow.projects.project_unit_of_work import (
    ProjectUnitOfWorkFactory,
)
from src.core.modules.project_management.application.projects.commands.lifecycle import (
    ProjectLifecycleMixin,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryMixin,
)
from src.core.platform.application.history.activity.activity_service import ActivityService
from src.core.platform.common.ids import generate_id
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.contract.repositories.time_management.time.contracts import TimeEntryRepository
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin
from src.core.shared.events.domain_event_context import DomainEventContext


class ProjectService(ProjectManagementModuleGuardMixin, ProjectLifecycleMixin, ProjectQueryMixin):
    """Project application service orchestrator."""

    def __init__(
        self,
        session: Session,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        assignment_repo: AssignmentRepository,
        time_entry_repo: TimeEntryRepository | None,
        user_session: UserSessionContext | None = None,
        activity_service: ActivityService | None = None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service=None,
        project_catalog_reader: ProjectCatalogReader | None = None,
        uow_factory: ProjectUnitOfWorkFactory | None = None,
        transactional_dispatcher=None,
        post_commit_bus=None,
    ):
        self._session: Session = session
        self._project_repo: ProjectRepository = project_repo
        self._task_repo: TaskRepository = task_repo
        self._dependency_repo: DependencyRepository = dependency_repo
        self._assignment_repo: AssignmentRepository = assignment_repo
        self._time_entry_repo = time_entry_repo
        self._user_session: UserSessionContext | None = user_session
        self._activity_service: ActivityService | None = activity_service
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._project_catalog_reader = project_catalog_reader
        self._uow_factory: ProjectUnitOfWorkFactory | None = uow_factory
        self._transactional_dispatcher = transactional_dispatcher
        self._post_commit_bus = post_commit_bus

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)


__all__ = ["ProjectService"]
