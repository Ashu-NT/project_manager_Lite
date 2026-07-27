from __future__ import annotations

from datetime import date, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infra.persistence.orm import Base
from src.core.platform.infrastructure.persistence.repositories.enterprise_calendar import (
    SqlAlchemyCalendarAssignmentRepository,
    SqlAlchemyCalendarExceptionRepository,
    SqlAlchemyCalendarRecurringEventRepository,
    SqlAlchemyCalendarWorkingRuleRepository,
    SqlAlchemyPlatformCalendarRepository,
    SqlAlchemyShiftPatternRepository,
)
from src.core.platform.calendar.domain.enterprise_calendar import (
    CalendarType,
    ExceptionType,
    ImpactType,
)
from src.core.platform.calendar.application.enterprise_calendar_service import (
    EnterpriseCalendarService,
)
from src.core.platform.calendar.application.calendar_assignment_service import (
    CalendarAssignmentService,
)
from src.core.platform.calendar.application.working_time_calculator import WorkingTimeCalculator


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
    return "test-org-001"


@pytest.fixture
def mock_user_session():
    from unittest.mock import MagicMock
    session = MagicMock()
    session.has_permission.return_value = True
    session.username = "test-admin"
    return session


@pytest.fixture
def mock_org_repo(db_session, org_id):
    from unittest.mock import MagicMock
    from dataclasses import dataclass

    @dataclass
    class FakeOrg:
        id: str = org_id

    repo = MagicMock()
    repo.get_active.return_value = FakeOrg()
    return repo


@pytest.fixture
def tenant_context(org_id):
    from unittest.mock import MagicMock
    from dataclasses import dataclass

    @dataclass
    class FakeOrg:
        id: str = org_id

    @dataclass
    class FakeContext:
        tenant_id: str = "tenant-platform-foundation"
        organization_id: str = org_id
        organization: FakeOrg | None = None

    context = MagicMock()
    context.require_active_organization_id.return_value = org_id
    context.get_active_organization_id.return_value = org_id
    context.get_active_organization.return_value = FakeOrg()
    context.get_active_tenant_id.return_value = "tenant-platform-foundation"
    context.require_organization_context.return_value = FakeContext(organization=FakeOrg())
    return context


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
def assignment_service(db_session, repos, mock_user_session):
    from unittest.mock import MagicMock
    pm_proj_repo = MagicMock()
    pm_proj_repo.save.return_value = None
    pm_proj_repo.get.return_value = None
    pm_proj_repo.list_for_calendar.return_value = []
    pm_res_repo = MagicMock()
    pm_res_repo.save.return_value = None
    pm_res_repo.get.return_value = None
    pm_res_repo.list_for_calendar.return_value = []
    return CalendarAssignmentService(
        session=db_session,
        calendar_repo=repos["calendar"],
        assignment_repo=repos["assignment"],
        project_assignment_repo=pm_proj_repo,
        resource_assignment_repo=pm_res_repo,
        user_session=mock_user_session,
    )


@pytest.fixture
def calculator():
    return WorkingTimeCalculator()


@pytest.fixture
def global_cal(cal_service, org_id):
    return cal_service.ensure_global_calendar(org_id)


# ---------------------------------------------------------------------------
# Tests — Assignments
# ---------------------------------------------------------------------------


def test_site_calendar_assignment(assignment_service, global_cal):
    a = assignment_service.assign_site_calendar(
        "site-hamburg", global_cal.id, is_default=True
    )
    assert a.site_id == "site-hamburg"
    assert a.calendar_id == global_cal.id

    fetched = assignment_service.get_site_calendar("site-hamburg")
    assert fetched is not None
    assert fetched.calendar_id == global_cal.id


def test_department_calendar_assignment(assignment_service, global_cal):
    assignment_service.assign_department_calendar("dept-eng", global_cal.id)
    fetched = assignment_service.get_department_calendar("dept-eng")
    assert fetched is not None
    assert fetched.department_id == "dept-eng"


def test_employee_calendar_assignment(assignment_service, global_cal):
    assignment_service.assign_employee_calendar("emp-jsmith", global_cal.id)
    fetched = assignment_service.get_employee_calendar("emp-jsmith")
    assert fetched is not None
    assert fetched.employee_id == "emp-jsmith"


def test_assignment_removal(assignment_service, global_cal):
    a = assignment_service.assign_site_calendar("site-x", global_cal.id)
    assignment_service.remove_site_assignment(a.id)
    fetched = assignment_service.get_site_calendar("site-x")
    assert fetched is None


def test_platform_calendar_assignments_normalize_dto_inputs(
    assignment_service, global_cal
):
    site_assignment = assignment_service.assign_site_calendar(
        "  site-hamburg  ",
        f"  {global_cal.id}  ",
        priority="2",
    )
    department_assignment = assignment_service.assign_department_calendar(
        "  dept-eng  ",
        f"  {global_cal.id}  ",
        priority="3",
    )
    employee_assignment = assignment_service.assign_employee_calendar(
        "  emp-jsmith  ",
        f"  {global_cal.id}  ",
        priority="4",
    )

    assert site_assignment.site_id == "site-hamburg"
    assert site_assignment.calendar_id == global_cal.id
    assert site_assignment.priority == 2

    assert department_assignment.department_id == "dept-eng"
    assert department_assignment.calendar_id == global_cal.id
    assert department_assignment.priority == 3

    assert employee_assignment.employee_id == "emp-jsmith"
    assert employee_assignment.calendar_id == global_cal.id
    assert employee_assignment.priority == 4

    assert assignment_service.get_site_calendar("site-hamburg").priority == 2
    assert assignment_service.get_department_calendar("dept-eng").priority == 3
    assert assignment_service.get_employee_calendar("emp-jsmith").priority == 4


# ---------------------------------------------------------------------------
# Tests — WorkingTimeCalculator
# ---------------------------------------------------------------------------


def test_working_time_calculator_derived_capacity(calculator):
    from src.core.platform.calendar.domain.enterprise_calendar import CalendarWorkingRule

    rules = [
        CalendarWorkingRule.create(
            "cal-1",
            weekday=0,
            is_working_day=True,
            start_time=time(8, 0),
            end_time=time(17, 0),
            break_minutes=60,
        )
    ]
    # 2026-06-01 is a Monday
    day = calculator.compute_day(
        working_rules=rules,
        exceptions=[],
        recurring_events=[],
        target_date=date(2026, 6, 1),
    )
    assert day.base_hours == 8.0
    assert day.available_hours == 8.0
    assert day.status == "AVAILABLE"


def test_holiday_makes_day_unavailable(calculator):
    from src.core.platform.calendar.domain.enterprise_calendar import (
        CalendarException,
        CalendarWorkingRule,
    )

    rules = [
        CalendarWorkingRule.create(
            "cal-1",
            weekday=0,
            is_working_day=True,
            start_time=time(8, 0),
            end_time=time(17, 0),
            break_minutes=60,
        )
    ]
    exceptions = [
        CalendarException.create(
            "cal-1",
            date(2026, 6, 1),
            ExceptionType.HOLIDAY.value,
            "Test Holiday",
            ImpactType.UNAVAILABLE.value,
        )
    ]
    day = calculator.compute_day(
        working_rules=rules,
        exceptions=exceptions,
        recurring_events=[],
        target_date=date(2026, 6, 1),
    )
    assert day.available_hours == 0.0
    assert day.status == "UNAVAILABLE"


def test_overtime_extra_capacity(calculator):
    from src.core.platform.calendar.domain.enterprise_calendar import (
        CalendarException,
        CalendarWorkingRule,
    )

    rules = [
        CalendarWorkingRule.create(
            "cal-1",
            weekday=0,
            is_working_day=True,
            start_time=time(8, 0),
            end_time=time(17, 0),
            break_minutes=60,
        )
    ]
    exceptions = [
        CalendarException.create(
            "cal-1",
            date(2026, 6, 1),
            ExceptionType.OVERTIME.value,
            "Saturday Overtime",
            ImpactType.EXTRA_CAPACITY.value,
            hours_override=4.0,
        )
    ]
    day = calculator.compute_day(
        working_rules=rules,
        exceptions=exceptions,
        recurring_events=[],
        target_date=date(2026, 6, 1),
    )
    assert day.available_hours == 12.0  # 8 base + 4 overtime
    assert "EXCEPTION:OVERTIME" in day.active_overrides


def test_non_working_day_returns_zero(calculator):
    from src.core.platform.calendar.domain.enterprise_calendar import CalendarWorkingRule

    rules = [
        CalendarWorkingRule.create(
            "cal-1",
            weekday=6,  # Sunday
            is_working_day=False,
        )
    ]
    day = calculator.compute_day(
        working_rules=rules,
        exceptions=[],
        recurring_events=[],
        target_date=date(2026, 6, 7),  # Sunday
    )
    assert day.available_hours == 0.0
    assert not day.is_working
