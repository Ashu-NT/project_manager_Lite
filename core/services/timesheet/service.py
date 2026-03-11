from __future__ import annotations

from sqlalchemy.orm import Session

from core.interfaces import (
    AssignmentRepository,
    ResourceRepository,
    TaskRepository,
    TimeEntryRepository,
    TimesheetPeriodRepository,
)
from core.services.audit.service import AuditService
from core.services.auth.session import UserSessionContext
from core.services.timesheet.entries import TimesheetEntriesMixin
from core.services.timesheet.periods import TimesheetPeriodsMixin
from core.services.timesheet.query import TimesheetQueryMixin
from core.services.timesheet.support import TimesheetSupportMixin


class TimesheetService(
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
    ):
        self._session: Session = session
        self._assignment_repo: AssignmentRepository = assignment_repo
        self._task_repo: TaskRepository = task_repo
        self._resource_repo: ResourceRepository = resource_repo
        self._time_entry_repo = time_entry_repo
        self._timesheet_period_repo = timesheet_period_repo
        self._user_session: UserSessionContext | None = user_session
        self._audit_service: AuditService | None = audit_service


__all__ = ["TimesheetService"]
