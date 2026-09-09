"""Enterprise calendar — PM integration tests: Capacity Calculator and Resolver.

Validates that ResourceCapacityCalculator correctly derives capacity from the
enterprise calendar engine and that the resolver source chain is correct.
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
from src.core.modules.project_management.infrastructure.persistence.repositories.scheduling.calendar_assignment import (
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
    context.require_active_scope_ids.return_value = FakeContext(organization=FakeOrg())
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
    global_cal, cal_service, assignment_service, resolver, db_session, tenant_context, org_id
):
    from datetime import datetime, timezone

    from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import DepartmentORM
    from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import SiteORM

    ctx = tenant_context.require_organization_context()
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            SiteORM(
                id="site-chain",
                tenant_id=ctx.tenant_id,
                organization_id=org_id,
                site_code="site-chain",
                name="site-chain",
                created_at=now,
                updated_at=now,
            ),
            DepartmentORM(
                id="dept-chain",
                tenant_id=ctx.tenant_id,
                organization_id=org_id,
                department_code="dept-chain",
                name="dept-chain",
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    db_session.commit()

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
