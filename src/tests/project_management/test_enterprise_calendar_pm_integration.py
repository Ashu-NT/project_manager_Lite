"""Enterprise calendar — PM integration tests.

Validates that PM resources, projects, and scheduling correctly delegate
to the Platform enterprise calendar engine.
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
from src.core.platform.calendar.domain.enterprise_calendar import (
    CalendarType,
    ExceptionType,
    ImpactType,
    RecurringEventType,
)
from src.core.platform.calendar.application.enterprise_calendar_service import (
    EnterpriseCalendarService,
)
from src.core.platform.calendar.application.working_rule_service import WorkingRuleService
from src.core.platform.calendar.application.calendar_exception_service import (
    CalendarExceptionService,
)
from src.core.platform.calendar.application.recurring_event_service import RecurringEventService
from src.core.platform.calendar.application.calendar_assignment_service import (
    CalendarAssignmentService,
)
from src.core.platform.calendar.application.enterprise_calendar_resolver import (
    EnterpriseCalendarResolver,
)
from src.core.platform.calendar.application.working_time_calculator import WorkingTimeCalculator
from src.core.modules.project_management.application.resources.enterprise_resource_availability import (
    EnterpriseResourceAvailabilityService,
)
from src.core.modules.project_management.application.resources.resource_capacity_calculator import (
    ResourceCapacityCalculator,
)
from src.core.modules.project_management.application.scheduling.calendars.project_calendar_adapter import (
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
    return "org-pm-test"


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
        tenant_id: str = "tenant-pm-calendar-integration"
        organization_id: str = org_id
        organization: FakeOrg | None = None

    context = MagicMock()
    context.require_active_organization_id.return_value = org_id
    context.get_active_organization_id.return_value = org_id
    context.get_active_organization.return_value = FakeOrg()
    context.get_active_tenant_id.return_value = "tenant-pm-calendar-integration"
    context.require_organization_context.return_value = FakeContext(
        organization=FakeOrg()
    )
    return context


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
def exc_service(db_session, repos, mock_user_session):
    return CalendarExceptionService(
        session=db_session,
        calendar_repo=repos["calendar"],
        exception_repo=repos["exception"],
        user_session=mock_user_session,
    )


@pytest.fixture
def recurring_service(db_session, repos, mock_user_session):
    return RecurringEventService(
        session=db_session,
        calendar_repo=repos["calendar"],
        event_repo=repos["recurring"],
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
def global_cal(cal_service, org_id, rule_service):
    cal = cal_service.ensure_global_calendar(org_id)
    rule_service.seed_standard_week(
        cal.id,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
    )
    return cal


def _make_resource_repo(resource_id, worker_type="EXTERNAL", employee_id=None):
    from dataclasses import dataclass
    from unittest.mock import MagicMock
    from src.core.modules.project_management.domain.enums import WorkerType

    @dataclass
    class FakeResource:
        id: str
        name: str
        worker_type: WorkerType
        employee_id: str = None

    repo = MagicMock()
    wt = WorkerType.EMPLOYEE if worker_type == "EMPLOYEE" else WorkerType.EXTERNAL
    repo.get.return_value = FakeResource(
        id=resource_id,
        name=f"Resource {resource_id}",
        worker_type=wt,
        employee_id=employee_id,
    )
    return repo


# ---------------------------------------------------------------------------
# Project Calendar
# ---------------------------------------------------------------------------


def test_project_calendar_assigned_and_resolved(
    global_cal, cal_service, assignment_service, resolver, org_id
):
    project_cal = cal_service.create_calendar(
        code="PRJ-REFIT",
        name="Refit Project",
        calendar_type=CalendarType.PROJECT.value,
    )
    assignment_service.assign_project_calendar("proj-001", project_cal.id)

    chain = resolver.get_source_chain(project_id="proj-001")
    assert any("PRJ" in s for s in chain)


def test_project_calendar_enables_weekend_work(
    global_cal, cal_service, assignment_service, rule_service, resolver
):
    project_cal = cal_service.create_calendar(
        code="PRJ-WEEKEND",
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
    assignment_service.assign_project_calendar("proj-weekend", project_cal.id)

    ctx = resolver.resolve_calendar_context(
        project_id="proj-weekend",
        target_date=date(2026, 6, 6),  # Saturday
    )
    assert ctx.available_hours > 0  # Saturday is now working via project override


def test_project_calendar_adapter_working_days(
    global_cal, assignment_service, resolver
):
    adapter = ProjectCalendarAdapter(
        resolver=resolver,
        assignment_service=assignment_service,
    )
    # Monday 2026-06-01 to Friday 2026-06-05 = 5 working days (global Mon-Fri)
    count = adapter.working_days_between("proj-x", date(2026, 6, 1), date(2026, 6, 5))
    assert count == 5


def test_project_calendar_adapter_add_working_days(
    global_cal, assignment_service, resolver
):
    adapter = ProjectCalendarAdapter(
        resolver=resolver,
        assignment_service=assignment_service,
    )
    # Starting Monday 2026-06-01, add 5 working days → Friday 2026-06-05
    result = adapter.add_working_days("proj-x", date(2026, 6, 1), 5)
    assert result == date(2026, 6, 5)


# ---------------------------------------------------------------------------
# Resource Calendar — External
# ---------------------------------------------------------------------------


def test_external_resource_uses_pm_resource_calendar(
    global_cal, cal_service, assignment_service, resolver, rule_service
):
    resource_cal = cal_service.create_calendar(
        code="RES-JDOE",
        name="John Doe Resource Calendar",
        calendar_type=CalendarType.RESOURCE.value,
    )
    rule_service.save_rule(
        resource_cal.id,
        weekday=0,  # Monday
        is_working_day=True,
        start_time=time(9, 0),
        end_time=time(15, 0),
        break_minutes=0,
        hours_override=6.0,
    )
    assignment_service.assign_resource_calendar("res-jdoe", resource_cal.id)

    resource_repo = _make_resource_repo("res-jdoe", worker_type="EXTERNAL")
    svc = EnterpriseResourceAvailabilityService(
        resolver=resolver, resource_repo=resource_repo
    )
    ctx = svc.get_availability("res-jdoe", target_date=date(2026, 6, 1))  # Monday
    assert ctx.available_hours == 6.0
    assert any("RESOURCE" in s for s in ctx.source_chain)


def test_resource_calendar_overrides_working_hours(
    global_cal, cal_service, assignment_service, resolver, rule_service
):
    resource_cal = cal_service.create_calendar(
        code="RES-PARTTIME",
        name="Part-time Resource",
        calendar_type=CalendarType.RESOURCE.value,
    )
    rule_service.save_rule(
        resource_cal.id,
        weekday=0,
        is_working_day=True,
        hours_override=4.0,  # Part-time: 4h instead of 8h
    )
    assignment_service.assign_resource_calendar("res-pt", resource_cal.id)

    resource_repo = _make_resource_repo("res-pt", worker_type="EXTERNAL")
    svc = EnterpriseResourceAvailabilityService(
        resolver=resolver, resource_repo=resource_repo
    )
    ctx = svc.get_availability("res-pt", target_date=date(2026, 6, 1))
    assert ctx.available_hours == 4.0


def test_resource_exception_vacation_unavailable(
    global_cal, cal_service, assignment_service, exc_service, resolver, rule_service
):
    resource_cal = cal_service.create_calendar(
        code="RES-VACATION",
        name="Vacation Resource",
        calendar_type=CalendarType.RESOURCE.value,
    )
    rule_service.save_rule(
        resource_cal.id, weekday=0, is_working_day=True, hours_override=8.0
    )
    assignment_service.assign_resource_calendar("res-vacation", resource_cal.id)
    exc_service.add_exception(
        resource_cal.id,
        exception_date=date(2026, 6, 1),
        exception_type=ExceptionType.VACATION.value,
        name="Annual Leave",
        impact_type=ImpactType.UNAVAILABLE.value,
    )

    resource_repo = _make_resource_repo("res-vacation", worker_type="EXTERNAL")
    svc = EnterpriseResourceAvailabilityService(
        resolver=resolver, resource_repo=resource_repo
    )
    ctx = svc.get_availability("res-vacation", target_date=date(2026, 6, 1))
    assert ctx.available_hours == 0.0
    assert ctx.status == "UNAVAILABLE"


# ---------------------------------------------------------------------------
# Employee-backed Resource
# ---------------------------------------------------------------------------


def test_employee_backed_resource_inherits_employee_calendar(
    global_cal, cal_service, assignment_service, resolver, rule_service
):
    emp_cal = cal_service.create_calendar(
        code="EMP-SMITH",
        name="John Smith Employee Calendar",
        calendar_type=CalendarType.EMPLOYEE.value,
    )
    rule_service.save_rule(
        emp_cal.id,
        weekday=0,
        is_working_day=True,
        hours_override=7.5,
    )
    assignment_service.assign_employee_calendar("emp-smith", emp_cal.id)

    resource_repo = _make_resource_repo(
        "res-smith", worker_type="EMPLOYEE", employee_id="emp-smith"
    )
    svc = EnterpriseResourceAvailabilityService(
        resolver=resolver, resource_repo=resource_repo
    )
    ctx = svc.get_availability("res-smith", target_date=date(2026, 6, 1))
    assert ctx.available_hours == 7.5
    assert any("EMP" in s for s in ctx.source_chain)


def test_employee_vacation_blocks_pm_resource(
    global_cal, cal_service, assignment_service, exc_service, resolver, rule_service
):
    emp_cal = cal_service.create_calendar(
        code="EMP-JONES",
        name="Jones Employee Calendar",
        calendar_type=CalendarType.EMPLOYEE.value,
    )
    rule_service.save_rule(emp_cal.id, weekday=0, is_working_day=True, hours_override=8.0)
    assignment_service.assign_employee_calendar("emp-jones", emp_cal.id)
    exc_service.add_exception(
        emp_cal.id,
        exception_date=date(2026, 6, 1),
        exception_type=ExceptionType.VACATION.value,
        name="Annual Leave",
        impact_type=ImpactType.UNAVAILABLE.value,
    )

    resource_repo = _make_resource_repo(
        "res-jones", worker_type="EMPLOYEE", employee_id="emp-jones"
    )
    svc = EnterpriseResourceAvailabilityService(
        resolver=resolver, resource_repo=resource_repo
    )
    ctx = svc.get_availability("res-jones", target_date=date(2026, 6, 1))
    assert ctx.available_hours == 0.0


def test_employee_training_reduces_pm_resource_capacity(
    global_cal, cal_service, assignment_service, recurring_service, resolver, rule_service
):
    emp_cal = cal_service.create_calendar(
        code="EMP-TRAINING",
        name="Training Employee Calendar",
        calendar_type=CalendarType.EMPLOYEE.value,
    )
    rule_service.save_rule(emp_cal.id, weekday=0, is_working_day=True, hours_override=8.0)
    assignment_service.assign_employee_calendar("emp-trainer", emp_cal.id)
    recurring_service.add_recurring_event(
        emp_cal.id,
        title="Weekly Safety Training",
        event_type=RecurringEventType.TRAINING.value,
        recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
        start_time=time(14, 0),
        end_time=time(16, 0),
        impact_type=ImpactType.UNAVAILABLE.value,
        effective_from=date(2026, 1, 1),
    )

    resource_repo = _make_resource_repo(
        "res-trainer", worker_type="EMPLOYEE", employee_id="emp-trainer"
    )
    svc = EnterpriseResourceAvailabilityService(
        resolver=resolver, resource_repo=resource_repo
    )
    ctx = svc.get_availability("res-trainer", target_date=date(2026, 6, 1))  # Monday
    assert ctx.available_hours < 8.0  # reduced by 2h training


def test_employee_backed_resource_does_not_duplicate_employee_rules(
    global_cal, cal_service, assignment_service, resolver, rule_service
):
    """
    An employee-backed resource should inherit employee calendar.
    PM resource calendar assignment should NOT be consulted for employee-backed resources.
    """
    emp_cal = cal_service.create_calendar(
        code="EMP-NODUPE",
        name="No Dupe Employee",
        calendar_type=CalendarType.EMPLOYEE.value,
    )
    rule_service.save_rule(emp_cal.id, weekday=0, is_working_day=True, hours_override=8.0)
    assignment_service.assign_employee_calendar("emp-nodupe", emp_cal.id)

    # Also assign a resource calendar with different hours — should NOT be used
    res_cal = cal_service.create_calendar(
        code="RES-NODUPE",
        name="No Dupe Resource",
        calendar_type=CalendarType.RESOURCE.value,
    )
    rule_service.save_rule(res_cal.id, weekday=0, is_working_day=True, hours_override=4.0)
    assignment_service.assign_resource_calendar("res-nodupe", res_cal.id)

    # Resource is EMPLOYEE-backed → should use employee calendar (8h), not resource calendar (4h)
    resource_repo = _make_resource_repo(
        "res-nodupe", worker_type="EMPLOYEE", employee_id="emp-nodupe"
    )
    svc = EnterpriseResourceAvailabilityService(
        resolver=resolver, resource_repo=resource_repo
    )
    ctx = svc.get_availability("res-nodupe", target_date=date(2026, 6, 1))
    assert ctx.available_hours == 8.0  # employee wins, not resource calendar


# ---------------------------------------------------------------------------
# Capacity Calculator
# ---------------------------------------------------------------------------


def test_capacity_derived_not_stored(
    global_cal, assignment_service, resolver
):
    resource_repo = _make_resource_repo("res-cap", worker_type="EXTERNAL")
    svc = EnterpriseResourceAvailabilityService(
        resolver=resolver, resource_repo=resource_repo
    )
    calc = ResourceCapacityCalculator(availability_service=svc)

    # Resource has no calendar → falls back to global (Mon-Fri 8h)
    summary = calc.compute("res-cap", date(2026, 6, 1), date(2026, 6, 5))
    assert summary.working_days == 5
    assert summary.base_hours == 40.0  # 5 days × 8h
    assert summary.available_hours == 40.0
    assert summary.capacity_percent == 100.0


def test_utilization_percent_calculated_correctly(
    global_cal, assignment_service, resolver
):
    resource_repo = _make_resource_repo("res-util", worker_type="EXTERNAL")
    svc = EnterpriseResourceAvailabilityService(
        resolver=resolver, resource_repo=resource_repo
    )
    calc = ResourceCapacityCalculator(availability_service=svc)

    # Assign 4h per day for Mon-Fri
    assigned = {
        date(2026, 6, 1): 4.0,
        date(2026, 6, 2): 4.0,
        date(2026, 6, 3): 4.0,
        date(2026, 6, 4): 4.0,
        date(2026, 6, 5): 4.0,
    }
    summary = calc.compute(
        "res-util", date(2026, 6, 1), date(2026, 6, 5),
        assigned_hours_by_date=assigned,
    )
    assert summary.assigned_hours == 20.0
    assert summary.available_hours == 40.0
    assert summary.utilization_percent == 50.0
    assert summary.remaining_hours == 20.0
    assert not summary.is_overallocated


def test_allocation_over_capacity_flagged(
    global_cal, assignment_service, resolver
):
    resource_repo = _make_resource_repo("res-over", worker_type="EXTERNAL")
    svc = EnterpriseResourceAvailabilityService(
        resolver=resolver, resource_repo=resource_repo
    )
    calc = ResourceCapacityCalculator(availability_service=svc)

    # Assign 10h on Monday (exceeds 8h)
    assigned = {date(2026, 6, 1): 10.0}
    summary = calc.compute(
        "res-over", date(2026, 6, 1), date(2026, 6, 1),
        assigned_hours_by_date=assigned,
    )
    assert summary.is_overallocated
    assert len(summary.conflicts) >= 1


# ---------------------------------------------------------------------------
# Resolver source chain
# ---------------------------------------------------------------------------


def test_resolver_source_chain_correct(
    global_cal, cal_service, assignment_service, resolver
):
    site_cal = cal_service.create_calendar(
        code="SITE-CHAIN",
        name="Site Chain",
        calendar_type=CalendarType.SITE.value,
    )
    dept_cal = cal_service.create_calendar(
        code="DEPT-CHAIN",
        name="Dept Chain",
        calendar_type=CalendarType.DEPARTMENT.value,
    )
    assignment_service.assign_site_calendar("site-chain", site_cal.id)
    assignment_service.assign_department_calendar("dept-chain", dept_cal.id)

    chain = resolver.get_source_chain(
        site_id="site-chain",
        department_id="dept-chain",
    )
    assert chain[0] == "GLOBAL"
    assert any("SITE" in s for s in chain)
    assert any("DEPT" in s for s in chain)
    assert chain.index("GLOBAL") < next(i for i, s in enumerate(chain) if "SITE" in s)
