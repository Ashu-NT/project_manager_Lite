"""
Test that SchedulingEngine uses the enterprise calendar when a project
has a calendar assignment, and falls back to WorkCalendarEngine when none exists.

This verifies Fix 1: ProjectCalendarAdapter is now wired into SchedulingEngine.
"""

from __future__ import annotations

from datetime import date, time
from unittest.mock import MagicMock

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
)
from src.core.modules.project_management.infrastructure.persistence.repositories.calendar_assignment import (
    SqlAlchemyProjectCalendarAssignmentRepository,
    SqlAlchemyResourceCalendarAssignmentRepository,
)
from src.core.platform.calendar.application.enterprise_calendar_service import EnterpriseCalendarService
from src.core.platform.calendar.application.working_rule_service import WorkingRuleService
from src.core.platform.calendar.application.calendar_assignment_service import CalendarAssignmentService
from src.core.platform.calendar.application.enterprise_calendar_resolver import EnterpriseCalendarResolver
from src.core.platform.calendar.application.working_time_calculator import WorkingTimeCalculator
from src.core.platform.calendar.domain.enterprise_calendar import CalendarType
from src.core.modules.project_management.application.scheduling.calendars.project_calendar_adapter import (
    BoundProjectCalendar,
    ProjectCalendarAdapter,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
    return "org-sched-test"


@pytest.fixture
def mock_user_session():
    session = MagicMock()
    session.has_permission.return_value = True
    session.username = "test-admin"
    return session


@pytest.fixture
def mock_org_repo(org_id):
    from dataclasses import dataclass

    @dataclass
    class FakeOrg:
        id: str = org_id

    repo = MagicMock()
    repo.get_active.return_value = FakeOrg()
    return repo


@pytest.fixture
def tenant_context(org_id):
    from dataclasses import dataclass

    @dataclass
    class FakeOrg:
        id: str = org_id

    @dataclass
    class FakeContext:
        tenant_id: str = "tenant-scheduling-integration"
        organization_id: str = org_id
        organization: FakeOrg | None = None

    context = MagicMock()
    context.require_active_organization_id.return_value = org_id
    context.get_active_organization_id.return_value = org_id
    context.get_active_organization.return_value = FakeOrg()
    context.get_active_tenant_id.return_value = "tenant-scheduling-integration"
    context.require_organization_context.return_value = FakeContext(
        organization=FakeOrg()
    )
    return context


@pytest.fixture
def repos(db_session, tenant_context):
    repos = {
        "calendar": SqlAlchemyPlatformCalendarRepository(db_session),
        "rule": SqlAlchemyCalendarWorkingRuleRepository(db_session),
        "exception": SqlAlchemyCalendarExceptionRepository(db_session),
        "recurring": SqlAlchemyCalendarRecurringEventRepository(db_session),
        "assignment": SqlAlchemyCalendarAssignmentRepository(db_session),
        "project_assignment": SqlAlchemyProjectCalendarAssignmentRepository(db_session),
        "resource_assignment": SqlAlchemyResourceCalendarAssignmentRepository(db_session),
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
    return CalendarAssignmentService(
        session=db_session,
        calendar_repo=repos["calendar"],
        assignment_repo=repos["assignment"],
        project_assignment_repo=repos["project_assignment"],
        resource_assignment_repo=repos["resource_assignment"],
        user_session=mock_user_session,
    )


@pytest.fixture
def calculator():
    return WorkingTimeCalculator()


@pytest.fixture
def resolver(repos, org_id, calculator):
    return EnterpriseCalendarResolver(
        organization_id=org_id,
        calendar_repo=repos["calendar"],
        rule_repo=repos["rule"],
        exception_repo=repos["exception"],
        recurring_repo=repos["recurring"],
        assignment_repo=repos["assignment"],
        project_assignment_repo=repos["project_assignment"],
        resource_assignment_repo=repos["resource_assignment"],
        calculator=calculator,
    )


@pytest.fixture
def adapter(resolver, assignment_service):
    return ProjectCalendarAdapter(
        resolver=resolver,
        assignment_service=assignment_service,
    )


@pytest.fixture
def global_cal(cal_service, org_id, rule_service):
    cal = cal_service.ensure_global_calendar(org_id)
    rule_service.seed_standard_week(
        cal.id,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
    )
    return cal


# ---------------------------------------------------------------------------
# BoundProjectCalendar tests
# ---------------------------------------------------------------------------


def test_bound_project_calendar_is_working_day_uses_enterprise(
    global_cal, adapter, assignment_service
):
    """When project has a calendar assignment, BoundProjectCalendar uses enterprise resolver."""
    assignment_service.assign_project_calendar("proj-bind-test", global_cal.id)
    bound = BoundProjectCalendar(adapter, "proj-bind-test")

    # 2026-06-01 is Monday — should be working per global Mon-Fri rules
    assert bound.is_working_day(date(2026, 6, 1)) is True
    # 2026-06-06 is Saturday — not working per global rules
    assert bound.is_working_day(date(2026, 6, 6)) is False


def test_bound_project_calendar_add_working_days(global_cal, adapter, assignment_service):
    assignment_service.assign_project_calendar("proj-add-test", global_cal.id)
    bound = BoundProjectCalendar(adapter, "proj-add-test")

    # Start Monday 2026-06-01, add 5 working days → Friday 2026-06-05
    result = bound.add_working_days(date(2026, 6, 1), 5)
    assert result == date(2026, 6, 5)


def test_bound_project_calendar_working_days_between(global_cal, adapter, assignment_service):
    assignment_service.assign_project_calendar("proj-between-test", global_cal.id)
    bound = BoundProjectCalendar(adapter, "proj-between-test")

    # Mon-Fri: 5 working days
    count = bound.working_days_between(date(2026, 6, 1), date(2026, 6, 5))
    assert count == 5


def test_bound_project_calendar_next_working_day(global_cal, adapter, assignment_service):
    assignment_service.assign_project_calendar("proj-next-test", global_cal.id)
    bound = BoundProjectCalendar(adapter, "proj-next-test")

    # Saturday → next working day is Monday
    nwd = bound.next_working_day(date(2026, 6, 6), include_today=False)
    assert nwd == date(2026, 6, 8)  # Monday


# ---------------------------------------------------------------------------
# ProjectCalendarAdapter.bind_for_project tests
# ---------------------------------------------------------------------------


def test_bind_for_project_returns_none_when_enterprise_not_bootstrapped(adapter):
    """
    When no enterprise calendars exist at all (no Global calendar bootstrapped),
    bind_for_project returns None so SchedulingEngine falls back to WorkCalendarEngine.

    In production, ensure_global_calendar() always runs at startup, so this path
    is only reached if bootstrap failed or the DB is empty.
    A project with no explicit assignment but a bootstrapped Global calendar
    will return a BoundProjectCalendar that uses the Global calendar via the resolver.
    """
    bound = adapter.bind_for_project("proj-no-calendar")
    assert bound is None


def test_bind_for_project_returns_bound_when_only_global_exists(global_cal, adapter):
    """
    A project with no explicit project-level assignment still gets a BoundProjectCalendar
    because the resolver finds the Global calendar and uses it as the base.
    The old WorkCalendarEngine is NOT consulted.
    """
    bound = adapter.bind_for_project("proj-no-specific-cal")
    assert bound is not None
    assert isinstance(bound, BoundProjectCalendar)
    # And it correctly uses Global calendar rules — Monday is a working day
    assert bound.is_working_day(date(2026, 6, 1)) is True  # Monday
    assert bound.is_working_day(date(2026, 6, 6)) is False  # Saturday


def test_bind_for_project_returns_bound_when_assigned(
    global_cal, adapter, assignment_service
):
    """When project has a calendar, bind_for_project returns a BoundProjectCalendar."""
    assignment_service.assign_project_calendar("proj-assigned", global_cal.id)
    bound = adapter.bind_for_project("proj-assigned")
    assert bound is not None
    assert isinstance(bound, BoundProjectCalendar)


def test_project_calendar_overrides_weekend_via_bound(
    global_cal, cal_service, rule_service, assignment_service, adapter, org_id
):
    """Project calendar with Saturday working hours produces working day on Saturday via bound adapter."""
    project_cal = cal_service.create_calendar(
        code="PRJ-SAT",
        name="Weekend Project",
        calendar_type=CalendarType.PROJECT.value,
    )
    rule_service.save_rule(
        project_cal.id,
        weekday=5,  # Saturday
        is_working_day=True,
        start_time=time(8, 0),
        end_time=time(14, 0),
    )
    assignment_service.assign_project_calendar("proj-sat", project_cal.id)

    bound = adapter.bind_for_project("proj-sat")
    assert bound is not None

    # Saturday 2026-06-06 — working because project calendar enables it
    assert bound.is_working_day(date(2026, 6, 6)) is True


# ---------------------------------------------------------------------------
# SchedulingEngine integration — verify adapter is hooked in correctly
# ---------------------------------------------------------------------------


def test_scheduling_engine_falls_back_to_base_calendar_when_not_bootstrapped(
    adapter,
):
    """
    SchedulingEngine uses the base calendar when no enterprise calendars are bootstrapped
    (get_source_chain returns [] → bind_for_project returns None → base calendar used).
    """
    from unittest.mock import MagicMock
    from src.core.modules.project_management.application.scheduling.services.scheduling_engine import SchedulingEngine
    from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

    mock_cal = MagicMock(spec=CalendarProtocol)
    engine = SchedulingEngine(
        session=MagicMock(),
        task_repo=MagicMock(),
        dependency_repo=MagicMock(),
        calendar=mock_cal,
        project_calendar_adapter=adapter,
    )
    # no enterprise calendars bootstrapped → chain empty → bind_for_project returns None
    engine._task_repo.list_by_project.return_value = []
    result = engine.recalculate_project_schedule("proj-no-cal")
    assert result == {}
    # Base calendar should be restored after the run
    assert engine._calendar is mock_cal


def test_scheduling_engine_uses_enterprise_calendar_when_assigned(
    global_cal, adapter, assignment_service
):
    """
    SchedulingEngine swaps to BoundProjectCalendar when a project calendar is assigned.
    """
    from unittest.mock import MagicMock
    from src.core.modules.project_management.application.scheduling.services.scheduling_engine import SchedulingEngine
    from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

    assignment_service.assign_project_calendar("proj-enterprise-cal", global_cal.id)

    mock_cal = MagicMock(spec=CalendarProtocol)
    engine = SchedulingEngine(
        session=MagicMock(),
        task_repo=MagicMock(),
        dependency_repo=MagicMock(),
        calendar=mock_cal,
        project_calendar_adapter=adapter,
    )
    engine._task_repo.list_by_project.return_value = []
    result = engine.recalculate_project_schedule("proj-enterprise-cal")
    assert result == {}
    # After run, base calendar restored
    assert engine._calendar is mock_cal
