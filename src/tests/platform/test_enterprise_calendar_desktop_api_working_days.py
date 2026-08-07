from __future__ import annotations

from datetime import date, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infra.persistence.orm import Base
from src.core.platform.infrastructure.persistence.repositories.time_management.calendar.enterprise_calendar import (
    SqlAlchemyCalendarAssignmentRepository,
    SqlAlchemyCalendarExceptionRepository,
    SqlAlchemyCalendarRecurringEventRepository,
    SqlAlchemyCalendarWorkingRuleRepository,
    SqlAlchemyPlatformCalendarRepository,
    SqlAlchemyShiftPatternRepository,
)
from src.core.platform.application.time_management.calendar.enterprise_calendar_service import (
    EnterpriseCalendarService,
)
from src.core.platform.application.time_management.calendar.definitions.working_rule_service import WorkingRuleService
from src.core.platform.application.time_management.calendar.assignment.calendar_assignment_service import (
    CalendarAssignmentService,
)
from src.core.platform.application.time_management.calendar.capacity.enterprise_calendar_resolver import (
    EnterpriseCalendarResolver,
)
from src.core.platform.application.time_management.calendar.capacity.working_time_calculator import WorkingTimeCalculator
from src.core.platform.api.desktop.time_management.calendar.enterprise_calendar import EnterpriseCalendarDesktopApi
from src.core.platform.api.desktop.time_management.calendar.models.enterprise_calendar import WorkingDaysCommand


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    db = Session()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def org_id():
    return "test-org-wd"


@pytest.fixture
def mock_user_session():
    from unittest.mock import MagicMock
    session = MagicMock()
    session.has_permission.return_value = True
    session.username = "test-admin"
    return session


@pytest.fixture
def tenant_context(org_id):
    from unittest.mock import MagicMock
    from dataclasses import dataclass

    @dataclass
    class FakeOrg:
        id: str = org_id

    @dataclass
    class FakeContext:
        tenant_id: str = "tenant-wd"
        organization_id: str = org_id
        organization: FakeOrg | None = None

    context = MagicMock()
    context.require_active_organization_id.return_value = org_id
    context.get_active_organization_id.return_value = org_id
    context.get_active_organization.return_value = FakeOrg()
    context.get_active_tenant_id.return_value = "tenant-wd"
    context.require_organization_context.return_value = FakeContext(organization=FakeOrg())
    return context


@pytest.fixture
def mock_org_repo(org_id):
    from unittest.mock import MagicMock
    from dataclasses import dataclass

    @dataclass
    class FakeOrg:
        id: str = org_id

    repo = MagicMock()
    repo.get_active.return_value = FakeOrg()
    return repo


@pytest.fixture
def repos(db_session, tenant_context):
    repos = {
        "calendar": SqlAlchemyPlatformCalendarRepository(db_session),
        "rule": SqlAlchemyCalendarWorkingRuleRepository(db_session),
        "exception": SqlAlchemyCalendarExceptionRepository(db_session),
        "recurring": SqlAlchemyCalendarRecurringEventRepository(db_session),
        "shift": SqlAlchemyShiftPatternRepository(db_session),
        "assignment": SqlAlchemyCalendarAssignmentRepository(db_session),
    }
    for repo in repos.values():
        if hasattr(repo, "_tenant_context_service"):
            repo._tenant_context_service = tenant_context
    return repos


@pytest.fixture
def cal_service(db_session, repos, mock_org_repo, mock_user_session, tenant_context):
    return EnterpriseCalendarService(
        session=db_session,
        calendar_repo=repos["calendar"],
        assignment_repo=repos["assignment"],
        organization_repo=mock_org_repo,
        user_session=mock_user_session,
        tenant_context_service=tenant_context,
    )


@pytest.fixture
def rule_service(db_session, repos, mock_user_session):
    return WorkingRuleService(
        session=db_session,
        calendar_repo=repos["calendar"],
        rule_repo=repos["rule"],
        user_session=mock_user_session,
    )


@pytest.fixture
def assignment_service(db_session, repos, mock_user_session):
    from unittest.mock import MagicMock
    return CalendarAssignmentService(
        session=db_session,
        calendar_repo=repos["calendar"],
        assignment_repo=repos["assignment"],
        project_assignment_repo=MagicMock(),
        resource_assignment_repo=MagicMock(),
        user_session=mock_user_session,
    )


@pytest.fixture
def resolver(repos, org_id):
    from unittest.mock import MagicMock
    return EnterpriseCalendarResolver(
        organization_id=org_id,
        calendar_repo=repos["calendar"],
        rule_repo=repos["rule"],
        exception_repo=repos["exception"],
        recurring_repo=repos["recurring"],
        assignment_repo=repos["assignment"],
        project_assignment_repo=MagicMock(),
        resource_assignment_repo=MagicMock(),
        calculator=WorkingTimeCalculator(),
    )


@pytest.fixture
def desktop_api(cal_service, rule_service, assignment_service, resolver):
    from unittest.mock import MagicMock
    return EnterpriseCalendarDesktopApi(
        calendar_service=cal_service,
        rule_service=rule_service,
        exception_service=MagicMock(),
        recurring_event_service=MagicMock(),
        shift_pattern_service=MagicMock(),
        assignment_service=assignment_service,
        resolver=resolver,
    )


def test_calculate_working_days_walks_forward_skipping_weekends(
    desktop_api, cal_service, rule_service, org_id
):
    global_cal = cal_service.ensure_global_calendar(org_id)
    rule_service.seed_standard_week(
        global_cal.id,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
    )

    # 2026-06-01 is a Monday; 5 working days later should land on Friday 2026-06-05.
    result = desktop_api.calculate_working_days(
        WorkingDaysCommand(start_date="2026-06-01", working_days=5)
    )

    assert result.ok is True
    assert result.data.start_date == "2026-06-01"
    assert result.data.end_date == "2026-06-05"
    assert result.data.working_days == 5


def test_calculate_working_days_zero_returns_start_date(desktop_api, cal_service, rule_service, org_id):
    global_cal = cal_service.ensure_global_calendar(org_id)
    rule_service.seed_standard_week(
        global_cal.id,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
    )

    result = desktop_api.calculate_working_days(
        WorkingDaysCommand(start_date="2026-06-01", working_days=0)
    )

    assert result.ok is True
    assert result.data.end_date == "2026-06-01"
    assert result.data.working_days == 0
