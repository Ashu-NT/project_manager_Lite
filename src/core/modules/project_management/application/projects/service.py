from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.cost_calendar import (
    CalendarEventRepository,
    CostRepository,
)
from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.application.projects.commands.lifecycle import (
    ProjectLifecycleMixin,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryMixin,
)
from src.core.platform.audit.application.audit_service import AuditService
from src.core.platform.auth.domain.session import UserSessionContext
from src.core.platform.common.interfaces import TimeEntryRepository
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin


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
        calendar_repo: CalendarEventRepository,
        cost_repo: CostRepository,
        user_session: UserSessionContext | None = None,
        audit_service: AuditService | None = None,
        module_catalog_service=None,
    ):
        self._session: Session = session
        self._project_repo: ProjectRepository = project_repo
        self._task_repo: TaskRepository = task_repo
        self._dependency_repo: DependencyRepository = dependency_repo
        self._assignment_repo: AssignmentRepository = assignment_repo
        self._time_entry_repo = time_entry_repo
        self._calendar_repo: CalendarEventRepository = calendar_repo
        self._cost_repo: CostRepository = cost_repo
        self._user_session: UserSessionContext | None = user_session
        self._audit_service: AuditService | None = audit_service
        self._module_catalog_service = module_catalog_service


__all__ = ["ProjectService"]

