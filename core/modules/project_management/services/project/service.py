from __future__ import annotations

from sqlalchemy.orm import Session

from core.modules.project_management.interfaces import (
    AssignmentRepository,
    CalendarEventRepository,
    CostRepository,
    DependencyRepository,
    ProjectRepository,
    TaskRepository,
)
from core.platform.common.interfaces import TimeEntryRepository
from core.platform.audit.service import AuditService
from src.core.platform.auth.domain.session import UserSessionContext
from core.modules.project_management.services.common.module_guard import ProjectManagementModuleGuardMixin
from core.modules.project_management.services.project.lifecycle import ProjectLifecycleMixin
from core.modules.project_management.services.project.query import ProjectQueryMixin


class ProjectService(ProjectManagementModuleGuardMixin, ProjectLifecycleMixin, ProjectQueryMixin):
    """Project service orchestrator: wiring repositories + composing mixins."""

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
