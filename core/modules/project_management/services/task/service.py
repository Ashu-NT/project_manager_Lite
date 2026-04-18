from __future__ import annotations

import os

from sqlalchemy.orm import Session

from core.modules.project_management.interfaces import (
    AssignmentRepository,
    CalendarEventRepository,
    CostRepository,
    DependencyRepository,
    ProjectRepository,
    ProjectResourceRepository,
    ResourceRepository,
    TaskRepository,
)
from core.platform.common.interfaces import TimeEntryRepository, TimesheetPeriodRepository
from src.core.platform.approval.application.approval_service import ApprovalService
from core.platform.audit.service import AuditService
from src.core.platform.auth.domain.session import UserSessionContext
from core.modules.project_management.services.common.module_guard import ProjectManagementModuleGuardMixin
from core.modules.project_management.services.scheduling import SchedulingEngine
from core.modules.project_management.services.task.assignment import TaskAssignmentMixin
from core.modules.project_management.services.task.assignment_bridge import TaskAssignmentBridgeMixin
from core.modules.project_management.services.task.dependency import TaskDependencyMixin
from core.modules.project_management.services.task.dependency_diagnostics import TaskDependencyDiagnosticsMixin
from core.modules.project_management.services.task.lifecycle import TaskLifecycleMixin
from core.modules.project_management.services.task.time_entries import TaskTimeEntryMixin
from core.modules.project_management.services.task.query import TaskQueryMixin
from core.modules.project_management.services.task.schedule_sync import TaskScheduleSyncMixin
from core.modules.project_management.services.task.validation import TaskValidationMixin
from core.modules.project_management.services.timesheet import TimesheetService
from core.modules.project_management.services.work_calendar.engine import WorkCalendarEngine


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
