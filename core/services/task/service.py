from __future__ import annotations

import os

from sqlalchemy.orm import Session

from core.interfaces import (
    AssignmentRepository,
    CalendarEventRepository,
    CostRepository,
    DependencyRepository,
    ProjectRepository,
    ProjectResourceRepository,
    ResourceRepository,
    TaskRepository,
)
from core.services.approval.service import ApprovalService
from core.services.audit.service import AuditService
from core.services.auth.session import UserSessionContext
from core.services.task.assignment import TaskAssignmentMixin
from core.services.task.dependency import TaskDependencyMixin
from core.services.task.dependency_diagnostics import TaskDependencyDiagnosticsMixin
from core.services.task.lifecycle import TaskLifecycleMixin
from core.services.task.query import TaskQueryMixin
from core.services.task.validation import TaskValidationMixin
from core.services.work_calendar.engine import WorkCalendarEngine


class TaskService(
    TaskLifecycleMixin,
    TaskDependencyDiagnosticsMixin,
    TaskDependencyMixin,
    TaskAssignmentMixin,
    TaskQueryMixin,
    TaskValidationMixin,
):
    def __init__(
        self,
        session: Session,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        assignment_repo: AssignmentRepository,
        resource_repo: ResourceRepository,
        cost_repo: CostRepository,
        calendar_repo: CalendarEventRepository,
        work_calendar_engine: WorkCalendarEngine,
        project_resource_repo: ProjectResourceRepository | None = None,
        project_repo: ProjectRepository | None = None,
        user_session: UserSessionContext | None = None,
        audit_service: AuditService | None = None,
        approval_service: ApprovalService | None = None,
    ):
        self._session: Session = session
        self._task_repo: TaskRepository = task_repo
        self._dependency_repo: DependencyRepository = dependency_repo
        self._assignment_repo: AssignmentRepository = assignment_repo
        self._resource_repo: ResourceRepository = resource_repo
        self._cost_repo: CostRepository = cost_repo
        self._calendar_repo: CalendarEventRepository = calendar_repo
        self._work_calendar_engine: WorkCalendarEngine = work_calendar_engine
        self._project_resource_repo: ProjectResourceRepository | None = project_resource_repo
        self._project_repo: ProjectRepository | None = project_repo
        self._user_session: UserSessionContext | None = user_session
        self._audit_service: AuditService | None = audit_service
        self._approval_service: ApprovalService | None = approval_service
        policy = os.getenv("PM_OVERALLOCATION_POLICY", "warn").strip().lower()
        self._overallocation_policy: str = "strict" if policy == "strict" else "warn"
        self._last_overallocation_warning: str | None = None

    def consume_last_overallocation_warning(self) -> str | None:
        warning = self._last_overallocation_warning
        self._last_overallocation_warning = None
        return warning
