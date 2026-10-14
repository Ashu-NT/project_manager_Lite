"""Enterprise calendar — PM integration tests: Employee-backed Resource Calendar.

Validates that employee-backed PM resources inherit employee calendars and
that employee exceptions/recurring events propagate correctly to PM resources.
"""

from __future__ import annotations

from datetime import UTC, date, time
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.application.resources.capacity.queries.availability import (
    ResourceAvailabilityQueryHandler,
)
from src.core.modules.project_management.domain.enums import (
    CostType,
    WorkerType,
)
from src.core.modules.project_management.infrastructure.persistence.orm.resource import (
    ResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.scheduling.calendar_assignment import (
    SqlAlchemyProjectCalendarAssignmentRepository,
    SqlAlchemyResourceCalendarAssignmentRepository,
)
from src.core.platform.application.time_management.calendar.assignment.commands.calendar_assignment_commands import (
    CalendarAssignmentCommandHandler,
)
from src.core.platform.application.time_management.calendar.assignment.queries.calendar_assignment_queries import (
    CalendarAssignmentQueryHandler,
)
from src.core.platform.application.time_management.calendar.capacity.platform_calendar_resolver import (
    PlatformCalendarResolver,
)
from src.core.platform.application.time_management.calendar.capacity.working_time_calculator import (
    WorkingTimeCalculator,
)
from src.core.platform.application.time_management.calendar.commands.platform_calendar_commands import (
    PlatformCalendarCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.calendar_exception_commands import (
    CalendarExceptionCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.recurring_event_commands import (
    RecurringEventCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.working_rule_commands import (
    WorkingRuleCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.calendar_exception_queries import (
    CalendarExceptionQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.recurring_event_queries import (
    RecurringEventQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.working_rule_queries import (
    WorkingRuleQueryHandler,
)
from src.core.platform.application.time_management.calendar.queries.platform_calendar_queries import (
    PlatformCalendarQueryHandler,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    CalendarType,
    ExceptionType,
    ImpactType,
    RecurringEventType,
)
from src.core.platform.infrastructure.persistence.repositories.time_management.calendar.enterprise_calendar import (
    SqlAlchemyCalendarAssignmentRepository,
    SqlAlchemyCalendarExceptionRepository,
    SqlAlchemyCalendarRecurringEventRepository,
    SqlAlchemyCalendarWorkingRuleRepository,
    SqlAlchemyPlatformCalendarRepository,
)
from src.infra.persistence.orm import Base

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
        "resource_assignment": SqlAlchemyResourceCalendarAssignmentRepository(
            db_session
        ),
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
def cal_commands(db_session, repos, mock_org_repo, mock_user_session, tenant_context):
    return PlatformCalendarCommandHandler(
        session=db_session,
        calendar_repo=repos["calendar"],
        assignment_repo=repos["assignment"],
        organization_repo=mock_org_repo,
        user_session=mock_user_session,
        tenant_context_service=tenant_context,
    )


@pytest.fixture
def cal_queries(db_session, repos, mock_org_repo, mock_user_session, tenant_context):
    return PlatformCalendarQueryHandler(
        calendar_repo=repos["calendar"],
        user_session=mock_user_session,
        tenant_context_service=tenant_context,
    )


@pytest.fixture
def rule_commands(db_session, repos, mock_user_session):
    return WorkingRuleCommandHandler(
        session=db_session,
        calendar_repo=repos["calendar"],
        rule_repo=repos["rule"],
        user_session=mock_user_session,
    )


@pytest.fixture
def rule_queries(db_session, repos, mock_user_session):
    return WorkingRuleQueryHandler(
        calendar_repo=repos["calendar"],
        rule_repo=repos["rule"],
        user_session=mock_user_session,
    )


@pytest.fixture
def exc_commands(db_session, repos, mock_user_session):
    return CalendarExceptionCommandHandler(
        session=db_session,
        calendar_repo=repos["calendar"],
        exception_repo=repos["exception"],
        user_session=mock_user_session,
    )


@pytest.fixture
def exc_queries(db_session, repos, mock_user_session):
    return CalendarExceptionQueryHandler(
        calendar_repo=repos["calendar"],
        exception_repo=repos["exception"],
        user_session=mock_user_session,
    )


@pytest.fixture
def recurring_commands(db_session, repos, mock_user_session):
    return RecurringEventCommandHandler(
        session=db_session,
        calendar_repo=repos["calendar"],
        event_repo=repos["recurring"],
        user_session=mock_user_session,
    )


@pytest.fixture
def recurring_queries(db_session, repos, mock_user_session):
    return RecurringEventQueryHandler(
        calendar_repo=repos["calendar"],
        event_repo=repos["recurring"],
        user_session=mock_user_session,
    )


@pytest.fixture
def assignment_commands(db_session, repos, mock_user_session):
    return CalendarAssignmentCommandHandler(
        session=db_session,
        calendar_repo=repos["calendar"],
        assignment_repo=repos["assignment"],
        project_assignment_repo=repos["project_assignment"],
        resource_assignment_repo=repos["resource_assignment"],
        user_session=mock_user_session,
    )


@pytest.fixture
def assignment_queries(db_session, repos, mock_user_session):
    return CalendarAssignmentQueryHandler(
        assignment_repo=repos["assignment"],
        project_assignment_repo=repos["project_assignment"],
        resource_assignment_repo=repos["resource_assignment"],
    )


@pytest.fixture
def calculator():
    return WorkingTimeCalculator()


@pytest.fixture
def resolver(repos, org_id, calculator):
    return PlatformCalendarResolver(
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
def global_cal(cal_commands, org_id, rule_commands):
    cal = cal_commands.ensure_global_calendar(org_id)
    rule_commands.seed_standard_week(
        cal.id,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
    )
    return cal


def _seed_department(db_session, tenant_context) -> str:
    from datetime import datetime

    from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import (
        DepartmentORM,
    )

    ctx = tenant_context.require_organization_context()
    department_id = "dept-pm-calendar-integration"
    if db_session.get(DepartmentORM, department_id) is not None:
        return department_id
    now = datetime.now(UTC)
    db_session.add(
        DepartmentORM(
            id=department_id,
            tenant_id=ctx.tenant_id,
            organization_id=ctx.organization_id,
            department_code=department_id,
            name="PM Calendar Integration Department",
            is_active=True,
            created_at=now,
            updated_at=now,
            version=1,
        )
    )
    db_session.commit()
    return department_id


def _seed_employee(db_session, tenant_context, employee_id: str) -> None:
    from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import (
        EmployeeORM,
    )

    ctx = tenant_context.require_organization_context()
    if db_session.get(EmployeeORM, employee_id) is not None:
        return
    department_id = _seed_department(db_session, tenant_context)
    db_session.add(
        EmployeeORM(
            id=employee_id,
            tenant_id=ctx.tenant_id,
            organization_id=ctx.organization_id,
            department_id=department_id,
            employee_code=employee_id,
            full_name=employee_id,
        )
    )
    db_session.commit()


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
# Employee-backed Resource
# ---------------------------------------------------------------------------


def test_employee_backed_resource_inherits_employee_calendar(
    global_cal,
    cal_commands,
    assignment_commands,
    resolver,
    rule_commands,
    db_session,
    tenant_context,
):
    emp_cal = cal_commands.create_calendar(
        code="EMP-SMITH",
        name="John Smith Employee Calendar",
        calendar_type=CalendarType.EMPLOYEE.value,
    )
    rule_commands.save_rule(
        emp_cal.id,
        weekday=0,
        is_working_day=True,
        hours_override=7.5,
    )
    _seed_employee(db_session, tenant_context, "emp-smith")
    assignment_commands.assign_employee_calendar("emp-smith", emp_cal.id)

    resource_repo = _make_resource_repo(
        "res-smith", worker_type="EMPLOYEE", employee_id="emp-smith"
    )
    svc = ResourceAvailabilityQueryHandler(
        resolver=resolver, resource_repo=resource_repo
    )
    ctx = svc.get_availability("res-smith", target_date=date(2026, 6, 1))
    assert ctx.available_hours == 7.5
    assert any("EMP" in s for s in ctx.source_chain)


def test_employee_vacation_blocks_pm_resource(
    global_cal,
    cal_commands,
    assignment_commands,
    exc_commands,
    resolver,
    rule_commands,
    db_session,
    tenant_context,
):
    emp_cal = cal_commands.create_calendar(
        code="EMP-JONES",
        name="Jones Employee Calendar",
        calendar_type=CalendarType.EMPLOYEE.value,
    )
    rule_commands.save_rule(
        emp_cal.id, weekday=0, is_working_day=True, hours_override=8.0
    )
    _seed_employee(db_session, tenant_context, "emp-jones")
    assignment_commands.assign_employee_calendar("emp-jones", emp_cal.id)
    exc_commands.add_exception(
        emp_cal.id,
        exception_date=date(2026, 6, 1),
        exception_type=ExceptionType.VACATION.value,
        name="Annual Leave",
        impact_type=ImpactType.UNAVAILABLE.value,
    )

    resource_repo = _make_resource_repo(
        "res-jones", worker_type="EMPLOYEE", employee_id="emp-jones"
    )
    svc = ResourceAvailabilityQueryHandler(
        resolver=resolver, resource_repo=resource_repo
    )
    ctx = svc.get_availability("res-jones", target_date=date(2026, 6, 1))
    assert ctx.available_hours == 0.0


def test_employee_training_reduces_pm_resource_capacity(
    global_cal,
    cal_commands,
    assignment_commands,
    recurring_commands,
    resolver,
    rule_commands,
    db_session,
    tenant_context,
):
    emp_cal = cal_commands.create_calendar(
        code="EMP-TRAINING",
        name="Training Employee Calendar",
        calendar_type=CalendarType.EMPLOYEE.value,
    )
    rule_commands.save_rule(
        emp_cal.id, weekday=0, is_working_day=True, hours_override=8.0
    )
    _seed_employee(db_session, tenant_context, "emp-trainer")
    assignment_commands.assign_employee_calendar("emp-trainer", emp_cal.id)
    recurring_commands.add_recurring_event(
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
    svc = ResourceAvailabilityQueryHandler(
        resolver=resolver, resource_repo=resource_repo
    )
    ctx = svc.get_availability("res-trainer", target_date=date(2026, 6, 1))  # Monday
    assert ctx.available_hours < 8.0  # reduced by 2h training


def test_employee_backed_resource_does_not_duplicate_employee_rules(
    global_cal,
    cal_commands,
    assignment_commands,
    resolver,
    rule_commands,
    db_session,
    tenant_context,
):
    """
    An employee-backed resource should inherit employee calendar.
    PM resource calendar assignment should NOT be consulted for employee-backed resources.
    """
    emp_cal = cal_commands.create_calendar(
        code="EMP-NODUPE",
        name="No Dupe Employee",
        calendar_type=CalendarType.EMPLOYEE.value,
    )
    rule_commands.save_rule(
        emp_cal.id, weekday=0, is_working_day=True, hours_override=8.0
    )
    _seed_employee(db_session, tenant_context, "emp-nodupe")
    assignment_commands.assign_employee_calendar("emp-nodupe", emp_cal.id)

    # Also assign a resource calendar with different hours — should NOT be used
    res_cal = cal_commands.create_calendar(
        code="RES-NODUPE",
        name="No Dupe Resource",
        calendar_type=CalendarType.RESOURCE.value,
    )
    rule_commands.save_rule(
        res_cal.id, weekday=0, is_working_day=True, hours_override=4.0
    )
    _seed_resource(db_session, tenant_context, "res-nodupe")
    assignment_commands.assign_resource_calendar("res-nodupe", res_cal.id)

    # Resource is EMPLOYEE-backed → should use employee calendar (8h), not resource calendar (4h)
    resource_repo = _make_resource_repo(
        "res-nodupe", worker_type="EMPLOYEE", employee_id="emp-nodupe"
    )
    svc = ResourceAvailabilityQueryHandler(
        resolver=resolver, resource_repo=resource_repo
    )
    ctx = svc.get_availability("res-nodupe", target_date=date(2026, 6, 1))
    assert ctx.available_hours == 8.0  # employee wins, not resource calendar


def test_resource_calendar_assignment_service_uses_dto_validation_and_normalization(
    cal_commands, assignment_commands, db_session, tenant_context
):
    res_cal = cal_commands.create_calendar(
        code="RES-NORMALIZED",
        name="Normalized Resource Calendar",
        calendar_type=CalendarType.RESOURCE.value,
    )
    _seed_resource(db_session, tenant_context, "res-normalized")

    assignment = assignment_commands.assign_resource_calendar(
        "  res-normalized  ",
        f"  {res_cal.id}  ",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        priority="3",
    )

    assert assignment.resource_id == "res-normalized"
    assert assignment.calendar_id == res_cal.id
    assert assignment.priority == 3

    with pytest.raises(ValidationError) as exc:
        assignment_commands.assign_resource_calendar(
            "res-normalized",
            res_cal.id,
            effective_from=date(2026, 12, 31),
            effective_to=date(2026, 1, 1),
        )
    assert exc.value.code == "RESOURCE_CALENDAR_ASSIGNMENT_DATE_RANGE_INVALID"
