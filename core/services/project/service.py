from __future__ import annotations

from sqlalchemy.orm import Session

from core.interfaces import (
    AssignmentRepository,
    CalendarEventRepository,
    CostRepository,
    DependencyRepository,
    ProjectRepository,
    TaskRepository,
)
from core.services.audit.service import AuditService
from core.services.auth.session import UserSessionContext
from core.services.project.lifecycle import ProjectLifecycleMixin
from core.services.project.query import ProjectQueryMixin


class ProjectService(ProjectLifecycleMixin, ProjectQueryMixin):
    """Project service orchestrator: wiring repositories + composing mixins."""

    def __init__(
        self,
        session: Session,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        assignment_repo: AssignmentRepository,
        calendar_repo: CalendarEventRepository,
        cost_repo: CostRepository,
        user_session: UserSessionContext | None = None,
        audit_service: AuditService | None = None,
    ):
        self._session: Session = session
        self._project_repo: ProjectRepository = project_repo
        self._task_repo: TaskRepository = task_repo
        self._dependency_repo: DependencyRepository = dependency_repo
        self._assignment_repo: AssignmentRepository = assignment_repo
        self._calendar_repo: CalendarEventRepository = calendar_repo
        self._cost_repo: CostRepository = cost_repo
        self._user_session: UserSessionContext | None = user_session
        self._audit_service: AuditService | None = audit_service


__all__ = ["ProjectService"]
