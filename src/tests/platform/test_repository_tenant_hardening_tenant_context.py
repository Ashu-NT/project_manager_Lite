from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.infrastructure.persistence.repositories.approval.approval import (
    SqlAlchemyApprovalRepository,
)
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.department.departments import (
    SqlAlchemyDepartmentRepository,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.documents.documents import (
    SqlAlchemyDocumentLinkRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyDocumentStructureRepository,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.employee.employee import (
    SqlAlchemyEmployeeRepository,
)
from src.core.platform.infrastructure.persistence.repositories.enterprise_calendar import (
    SqlAlchemyCalendarAssignmentRepository,
    SqlAlchemyCalendarExceptionRepository,
    SqlAlchemyCalendarRecurringEventRepository,
    SqlAlchemyCalendarWorkingRuleRepository,
    SqlAlchemyPlatformCalendarRepository,
    SqlAlchemyShiftPatternRepository,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.party.party import (
    SqlAlchemyPartyRepository,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.site.sites import (
    SqlAlchemySiteRepository,
)
from src.core.platform.infrastructure.persistence.repositories.time_management.time.time import (
    SqlAlchemyTimeEntryRepository,
    SqlAlchemyTimesheetPeriodRepository,
)


@pytest.mark.parametrize(
    ("repo_factory", "operation"),
    [
        (SqlAlchemySiteRepository, lambda repo: repo.get("site-1")),
        (SqlAlchemyDepartmentRepository, lambda repo: repo.get("department-1")),
        (SqlAlchemyEmployeeRepository, lambda repo: repo.get("employee-1")),
        (SqlAlchemyPartyRepository, lambda repo: repo.get("party-1")),
        (SqlAlchemyDocumentStructureRepository, lambda repo: repo.get("structure-1")),
        (SqlAlchemyDocumentRepository, lambda repo: repo.get("document-1")),
        (SqlAlchemyDocumentLinkRepository, lambda repo: repo.get("link-1")),
        (SqlAlchemyApprovalRepository, lambda repo: repo.get("approval-1")),
        (SqlAlchemyAuditRepository, lambda repo: repo.list_recent(limit=1)),
        (SqlAlchemyTimeEntryRepository, lambda repo: repo.get("time-entry-1")),
        (SqlAlchemyTimesheetPeriodRepository, lambda repo: repo.get("timesheet-1")),
        (SqlAlchemyPlatformCalendarRepository, lambda repo: repo.get("calendar-1")),
        (SqlAlchemyCalendarWorkingRuleRepository, lambda repo: repo.get("rule-1")),
        (SqlAlchemyCalendarExceptionRepository, lambda repo: repo.get("exception-1")),
        (SqlAlchemyCalendarRecurringEventRepository, lambda repo: repo.get("event-1")),
        (SqlAlchemyShiftPatternRepository, lambda repo: repo.get("shift-1")),
        (SqlAlchemyCalendarAssignmentRepository, lambda repo: repo.list_site_assignments("site-1")),
    ],
)
def test_platform_repositories_require_tenant_context_service(
    session, repo_factory, operation
) -> None:
    repo = repo_factory(session)
    with pytest.raises(BusinessRuleError, match="TenantContextService"):
        operation(repo)
