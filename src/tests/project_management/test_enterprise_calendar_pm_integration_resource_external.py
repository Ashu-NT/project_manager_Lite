"""Enterprise calendar — PM integration tests: External Resource Calendar.

Validates that external PM resources correctly delegate availability
resolution to the Platform enterprise calendar engine.
"""

from __future__ import annotations

from datetime import date, time
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.domain.enums import (
    CostType,
    ProjectStatus,
    WorkerType,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import ProjectORM
from src.core.modules.project_management.infrastructure.persistence.orm.resource import ResourceORM
from src.core.platform.infrastructure.persistence.repositories.time_management.calendar.enterprise_calendar import (
    SqlAlchemyCalendarAssignmentRepository,
    SqlAlchemyCalendarExceptionRepository,
    SqlAlchemyCalendarRecurringEventRepository,
    SqlAlchemyCalendarWorkingRuleRepository,
    SqlAlchemyPlatformCalendarRepository,
)
from src.infra.persistence.orm import Base
from src.core.modules.project_management.infrastructure.persistence.repositories.calendar_assignment import (
    SqlAlchemyProjectCalendarAssignmentRepository,
    SqlAlchemyResourceCalendarAssignmentRepository,
)
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    CalendarType,
    ExceptionType,
    ImpactType,
    RecurringEventType,
)
from src.core.platform.application.time_management.calendar.enterprise_calendar_service import (
    EnterpriseCalendarService,
)
from src.core.platform.application.time_management.calendar.definitions.working_rule_service import WorkingRuleService
from src.core.platform.application.time_management.calendar.definitions.calendar_exception_service import (
    CalendarExceptionService,
)
from src.core.platform.application.time_management.calendar.definitions.recurring_event_service import RecurringEventService
from src.core.platform.application.time_management.calendar.assignment.calendar_assignment_service import (
    CalendarAssignmentService,
)
from src.core.platform.application.time_management.calendar.capacity.enterprise_calendar_resolver import (
    EnterpriseCalendarResolver,
)
from src.core.platform.application.time_management.calendar.capacity.working_time_calculator import WorkingTimeCalculator
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


def _seed_resource(db_session, tenant_context, resource_id: str) -> None:
    ctx = tenant_context.require_organization_context()
    if db_session.get(ResourceORM, resource_id) is not None:
        return
    db_session.add(
        ResourceORM(
            id=resource_id,
            tenant_id=ctx.tenant_id,
            organization_id=ctx.organization_id,
            name=f"Resource {resource_id}",
            role="Planner",
            hourly_rate=100.0,
            is_active=True,
            capacity_percent=100.0,
            cost_type=CostType.LABOR,
            worker_type=WorkerType.EXTERNAL,
            version=1,
        )
    )
    db_session.commit()


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
# Resource Calendar — External
# ---------------------------------------------------------------------------


def test_external_resource_uses_pm_resource_calendar(
    global_cal, cal_service, assignment_service, resolver, rule_service, db_session, tenant_context
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
    _seed_resource(db_session, tenant_context, "res-jdoe")
    assignment_service.assign_resource_calendar("res-jdoe", resource_cal.id)

    resource_repo = _make_resource_repo("res-jdoe", worker_type="EXTERNAL")
    svc = EnterpriseResourceAvailabilityService(
        resolver=resolver, resource_repo=resource_repo
    )
    ctx = svc.get_availability("res-jdoe", target_date=date(2026, 6, 1))  # Monday
    assert ctx.available_hours == 6.0
    assert any("RESOURCE" in s for s in ctx.source_chain)


def test_resource_calendar_overrides_working_hours(
    global_cal, cal_service, assignment_service, resolver, rule_service, db_session, tenant_context
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
    _seed_resource(db_session, tenant_context, "res-pt")
    assignment_service.assign_resource_calendar("res-pt", resource_cal.id)

    resource_repo = _make_resource_repo("res-pt", worker_type="EXTERNAL")
    svc = EnterpriseResourceAvailabilityService(
        resolver=resolver, resource_repo=resource_repo
    )
    ctx = svc.get_availability("res-pt", target_date=date(2026, 6, 1))
    assert ctx.available_hours == 4.0


def test_resource_exception_vacation_unavailable(
    global_cal, cal_service, assignment_service, exc_service, resolver, rule_service, db_session, tenant_context
):
    resource_cal = cal_service.create_calendar(
        code="RES-VACATION",
        name="Vacation Resource",
        calendar_type=CalendarType.RESOURCE.value,
    )
    rule_service.save_rule(
        resource_cal.id, weekday=0, is_working_day=True, hours_override=8.0
    )
    _seed_resource(db_session, tenant_context, "res-vacation")
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
