from __future__ import annotations

import os

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentMixin,
)
from src.core.modules.project_management.application.tasks.commands.assignment_bridge import (
    TaskAssignmentBridgeMixin,
)
from src.core.modules.project_management.application.tasks.commands.dependency import (
    TaskDependencyMixin,
)
from src.core.modules.project_management.application.tasks.commands.lifecycle import (
    TaskLifecycleMixin,
)
from src.core.modules.project_management.application.tasks.commands.schedule_sync import (
    TaskScheduleSyncMixin,
)
from src.core.modules.project_management.application.tasks.commands.time_entries import (
    TaskTimeEntryMixin,
)
from src.core.modules.project_management.application.tasks.commands.validation import (
    TaskValidationMixin,
)
from src.core.modules.project_management.application.tasks.queries.dependency_diagnostics import (
    TaskDependencyDiagnosticsMixin,
)
from src.core.modules.project_management.application.tasks.queries.task_query import (
    TaskQueryMixin,
)
from src.core.modules.project_management.contracts.repositories.cost_calendar import (
    CalendarEventRepository,
    CostRepository,
)
from src.core.modules.project_management.contracts.repositories.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.platform.approval.application.approval_service import ApprovalService
from src.core.platform.audit.application.audit_service import AuditService
from src.core.platform.auth.domain.session import UserSessionContext
from src.core.platform.common.interfaces import TimeEntryRepository, TimesheetPeriodRepository
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin
from src.core.modules.project_management.application.resources import TimesheetService
from src.core.modules.project_management.application.scheduling import (
    SchedulingEngine,
    WorkCalendarEngine,
)


class TaskService(
    ProjectManagementModuleGuardMixin,
    TaskScheduleSyncMixin,
    TaskLifecycleMixin,
    TaskDependencyDiagnosticsMixin,
    TaskDependencyMixin,
    TaskAssignmentMixin,
    TaskTimeEntryMixin,
    TaskAssignmentBridgeMixin,
    TaskQueryMixin,
    TaskValidationMixin,
):
    """Task application service orchestrator."""

    def __init__(
        self,
        session: Session,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        assignment_repo: AssignmentRepository,
        time_entry_repo: TimeEntryRepository | None,
        timesheet_period_repo: TimesheetPeriodRepository | None,
        timesheet_service: TimesheetService | None,
        resource_repo: ResourceRepository,
        cost_repo: CostRepository,
        calendar_repo: CalendarEventRepository,
        work_calendar_engine: WorkCalendarEngine,
        scheduling_engine: SchedulingEngine | None = None,
        project_resource_repo: ProjectResourceRepository | None = None,
        project_repo: ProjectRepository | None = None,
        user_session: UserSessionContext | None = None,
        audit_service: AuditService | None = None,
        approval_service: ApprovalService | None = None,
        module_catalog_service=None,
    ):
        self._session: Session = session
        self._task_repo: TaskRepository = task_repo
        self._dependency_repo: DependencyRepository = dependency_repo
        self._assignment_repo: AssignmentRepository = assignment_repo
        self._time_entry_repo = time_entry_repo
        self._timesheet_period_repo = timesheet_period_repo
        self._timesheet_service = timesheet_service
        self._resource_repo: ResourceRepository = resource_repo
        self._cost_repo: CostRepository = cost_repo
        self._calendar_repo: CalendarEventRepository = calendar_repo
        self._work_calendar_engine: WorkCalendarEngine = work_calendar_engine
        self._scheduling_engine: SchedulingEngine | None = scheduling_engine
        self._project_resource_repo: ProjectResourceRepository | None = project_resource_repo
        self._project_repo: ProjectRepository | None = project_repo
        self._user_session: UserSessionContext | None = user_session
        self._audit_service: AuditService | None = audit_service
        self._approval_service: ApprovalService | None = approval_service
        self._module_catalog_service = module_catalog_service
        policy = os.getenv("PM_OVERALLOCATION_POLICY", "warn").strip().lower()
        self._overallocation_policy: str = "strict" if policy == "strict" else "warn"
        self._last_overallocation_warning: str | None = None

    def consume_last_overallocation_warning(self) -> str | None:
        warning = self._last_overallocation_warning
        self._last_overallocation_warning = None
        return warning


__all__ = ["TaskService"]

