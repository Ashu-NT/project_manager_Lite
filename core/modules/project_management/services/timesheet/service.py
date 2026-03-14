from __future__ import annotations

from sqlalchemy.orm import Session

from core.platform.common.interfaces import (
    AssignmentRepository,
    ResourceRepository,
    TaskRepository,
    TimeEntryRepository,
    TimesheetPeriodRepository,
)
from core.platform.audit.service import AuditService
from core.platform.auth.session import UserSessionContext
from core.modules.project_management.services.common.module_guard import ProjectManagementModuleGuardMixin
from core.modules.project_management.services.timesheet.entries import TimesheetEntriesMixin
from core.modules.project_management.services.timesheet.periods import TimesheetPeriodsMixin
from core.modules.project_management.services.timesheet.query import TimesheetQueryMixin
from core.modules.project_management.services.timesheet.support import TimesheetSupportMixin


class TimesheetService(
    ProjectManagementModuleGuardMixin,
    TimesheetEntriesMixin,
    TimesheetPeriodsMixin,
    TimesheetQueryMixin,
    TimesheetSupportMixin,
):
    """Timesheet service orchestrator: reusable time-entry and period workflows."""

    def __init__(
        self,
        session: Session,
        assignment_repo: AssignmentRepository,
        task_repo: TaskRepository,
        resource_repo: ResourceRepository,
        time_entry_repo: TimeEntryRepository | None,
        timesheet_period_repo: TimesheetPeriodRepository | None,
        user_session: UserSessionContext | None = None,
        audit_service: AuditService | None = None,
        module_catalog_service=None,
    ):
        self._session: Session = session
        self._assignment_repo: AssignmentRepository = assignment_repo
        self._task_repo: TaskRepository = task_repo
        self._resource_repo: ResourceRepository = resource_repo
        self._time_entry_repo = time_entry_repo
        self._timesheet_period_repo = timesheet_period_repo
        self._user_session: UserSessionContext | None = user_session
        self._audit_service: AuditService | None = audit_service
        self._module_catalog_service = module_catalog_service


__all__ = ["TimesheetService"]
