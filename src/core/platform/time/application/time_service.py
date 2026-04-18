from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.platform.audit.application.audit_service import AuditService
from src.core.platform.auth.domain.session import UserSessionContext
from src.core.platform.org.contracts import EmployeeRepository
from src.core.platform.time.application.timesheet_entries import TimesheetEntriesMixin
from src.core.platform.time.application.timesheet_periods import TimesheetPeriodsMixin
from src.core.platform.time.application.timesheet_query import TimesheetQueryMixin
from src.core.platform.time.application.timesheet_review import TimesheetReviewMixin
from src.core.platform.time.application.timesheet_support import TimesheetSupportMixin
from src.core.platform.time.contracts import (
    TimeEntryRepository,
    TimesheetPeriodRepository,
    WorkAllocationRepository,
    WorkOwnerRepository,
    WorkResourceRepository,
)


class TimeService(
    TimesheetEntriesMixin,
    TimesheetPeriodsMixin,
    TimesheetQueryMixin,
    TimesheetReviewMixin,
    TimesheetSupportMixin,
):
    """Shared time-entry and timesheet-period workflows for platform consumers."""

    def __init__(
        self,
        session: Session,
        assignment_repo: WorkAllocationRepository,
        task_repo: WorkOwnerRepository,
        resource_repo: WorkResourceRepository,
        employee_repo: EmployeeRepository | None,
        time_entry_repo: TimeEntryRepository | None,
        timesheet_period_repo: TimesheetPeriodRepository | None,
        user_session: UserSessionContext | None = None,
        audit_service: AuditService | None = None,
        module_catalog_service=None,
    ):
        self._session: Session = session
        self._work_allocation_repo: WorkAllocationRepository = assignment_repo
        self._assignment_repo: WorkAllocationRepository = assignment_repo
        self._work_owner_repo: WorkOwnerRepository = task_repo
        self._task_repo: WorkOwnerRepository = task_repo
        self._resource_repo: WorkResourceRepository = resource_repo
        self._employee_repo: EmployeeRepository | None = employee_repo
        self._time_entry_repo = time_entry_repo
        self._timesheet_period_repo = timesheet_period_repo
        self._user_session: UserSessionContext | None = user_session
        self._audit_service: AuditService | None = audit_service
        self._module_catalog_service = module_catalog_service


__all__ = ["TimeService"]
