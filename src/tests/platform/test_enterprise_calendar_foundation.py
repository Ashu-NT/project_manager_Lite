"""Enterprise calendar engine — platform foundation tests."""

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
    PlatformCalendar,
    RecurringEventType,
    PatternType,
)
from src.core.platform.calendar.application.enterprise_calendar_service import (
    EnterpriseCalendarService,
)
from src.core.platform.calendar.application.working_rule_service import WorkingRuleService
from src.core.platform.calendar.application.calendar_exception_service import (
    CalendarExceptionService,
)
from src.core.platform.calendar.application.recurring_event_service import RecurringEventService
from src.core.platform.calendar.application.shift_pattern_service import ShiftPatternService
from src.core.platform.calendar.application.calendar_assignment_service import (
    CalendarAssignmentService,
)
from src.core.platform.calendar.application.enterprise_calendar_resolver import (
    EnterpriseCalendarResolver,
)
from src.core.platform.calendar.application.working_time_calculator import WorkingTimeCalculator
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError

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
def repos(db_session):
    return {
        "calendar": SqlAlchemyPlatformCalendarRepository(db_session),
        "rule": SqlAlchemyCalendarWorkingRuleRepository(db_session),
        "exception": SqlAlchemyCalendarExceptionRepository(db_session),
        "recurring": SqlAlchemyCalendarRecurringEventRepository(db_session),
        "shift": SqlAlchemyShiftPatternRepository(db_session),
        "assignment": SqlAlchemyCalendarAssignmentRepository(db_session),
    }


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

    context = MagicMock()
    context.require_active_organization_id.return_value = org_id
    context.get_active_organization_id.return_value = org_id
    context.get_active_organization.return_value = FakeOrg()
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
def shift_service(db_session, repos, mock_org_repo, mock_user_session, tenant_context):
    return ShiftPatternService(
        session=db_session,
        pattern_repo=repos["shift"],
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
def resolver(repos, org_id, calculator):
    from unittest.mock import MagicMock
    pm_proj_repo = MagicMock()
    pm_proj_repo.get.return_value = None
    pm_res_repo = MagicMock()
    pm_res_repo.get.return_value = None
    return EnterpriseCalendarResolver(
        organization_id=org_id,
        calendar_repo=repos["calendar"],
        rule_repo=repos["rule"],
        exception_repo=repos["exception"],
        recurring_repo=repos["recurring"],
        assignment_repo=repos["assignment"],
        project_assignment_repo=pm_proj_repo,
        resource_assignment_repo=pm_res_repo,
        calculator=calculator,
    )


@pytest.fixture
def global_cal(cal_service, org_id):
    return cal_service.ensure_global_calendar(org_id)


# ---------------------------------------------------------------------------
# Tests — Calendar CRUD
# ---------------------------------------------------------------------------


def test_global_calendar_created_on_bootstrap(cal_service, org_id):
    cal = cal_service.ensure_global_calendar(org_id)
    assert cal.calendar_type == CalendarType.GLOBAL.value
    assert cal.organization_id == org_id
    assert cal.is_active


def test_global_calendar_idempotent(cal_service, org_id):
    cal1 = cal_service.ensure_global_calendar(org_id)
    cal2 = cal_service.ensure_global_calendar(org_id)
    assert cal1.id == cal2.id


def test_create_site_calendar(cal_service, org_id):
    cal = cal_service.create_calendar(
        code="SITE-HH",
        name="Hamburg Site",
        calendar_type=CalendarType.SITE.value,
        timezone="Europe/Berlin",
    )
    assert cal.code == "SITE-HH"
    assert cal.calendar_type == CalendarType.SITE.value
    assert cal.timezone == "Europe/Berlin"


def test_create_calendar_duplicate_code_raises(cal_service, org_id):
    cal_service.create_calendar(
        code="DUPE", name="First", calendar_type=CalendarType.DEPARTMENT.value
    )
    with pytest.raises(ValidationError, match="already exists"):
        cal_service.create_calendar(
            code="DUPE", name="Second", calendar_type=CalendarType.DEPARTMENT.value
        )


def test_create_calendar_invalid_type_raises(cal_service):
    with pytest.raises(ValidationError, match="Invalid calendar_type"):
        cal_service.create_calendar(
            code="BAD", name="Bad", calendar_type="NONEXISTENT"
        )


def test_update_calendar(cal_service, global_cal):
    updated = cal_service.update_calendar(
        global_cal.id, name="Global (Updated)", timezone="Europe/Berlin"
    )
    assert updated.name == "Global (Updated)"
    assert updated.timezone == "Europe/Berlin"
    assert updated.version == global_cal.version + 1


def test_delete_calendar_not_assigned(cal_service, org_id):
    cal = cal_service.create_calendar(
        code="TODELETE", name="Temp", calendar_type=CalendarType.PROJECT.value
    )
    cal_service.delete_calendar(cal.id)
    with pytest.raises(NotFoundError):
        cal_service.get_calendar(cal.id)


def test_delete_calendar_blocked_if_assigned(
    cal_service, assignment_service, global_cal
):
    assignment_service.assign_site_calendar("site-x", global_cal.id)
    with pytest.raises(BusinessRuleError, match="assigned"):
        cal_service.delete_calendar(global_cal.id)


def test_list_calendars_filtered_by_type(cal_service, global_cal, org_id):
    cal_service.create_calendar(
        code="SITE-A", name="Site A", calendar_type=CalendarType.SITE.value
    )
    global_cals = cal_service.list_calendars(calendar_type=CalendarType.GLOBAL.value)
    assert all(c.calendar_type == CalendarType.GLOBAL.value for c in global_cals)
    assert len(global_cals) >= 1


# ---------------------------------------------------------------------------
# Tests — Working Rules
# ---------------------------------------------------------------------------


def test_working_rule_seed_standard_week(rule_service, global_cal):
    rules = rule_service.seed_standard_week(
        global_cal.id,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
    )
    assert len(rules) == 7
    working = [r for r in rules if r.is_working_day]
    assert len(working) == 5  # Mon-Fri
    # 8 hours: 9h window - 1h break
    for r in working:
        assert r.compute_hours() == 8.0


def test_working_rule_start_before_end_enforced(rule_service, global_cal):
    with pytest.raises(ValidationError, match="before end_time"):
        rule_service.save_rule(
            global_cal.id,
            weekday=0,
            is_working_day=True,
            start_time=time(17, 0),
            end_time=time(8, 0),
        )


def test_working_rule_non_working_day_zero_hours(rule_service, global_cal):
    rule = rule_service.save_rule(global_cal.id, weekday=6, is_working_day=False)
    assert rule.compute_hours() == 0.0


def test_working_rule_hours_override(rule_service, global_cal):
    rule = rule_service.save_rule(
        global_cal.id,
        weekday=0,
        is_working_day=True,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
        hours_override=6.0,
    )
    assert rule.compute_hours() == 6.0


# ---------------------------------------------------------------------------
# Tests — Exceptions
# ---------------------------------------------------------------------------


def test_exception_types_persist_correctly(exc_service, global_cal):
    exc = exc_service.add_exception(
        global_cal.id,
        exception_date=date(2026, 12, 25),
        exception_type=ExceptionType.HOLIDAY.value,
        name="Christmas",
        impact_type=ImpactType.UNAVAILABLE.value,
    )
    assert exc.exception_type == ExceptionType.HOLIDAY.value
    assert exc.impact_type == ImpactType.UNAVAILABLE.value
    assert exc.exception_date == date(2026, 12, 25)


def test_exception_invalid_type_raises(exc_service, global_cal):
    with pytest.raises(ValidationError, match="Invalid exception_type"):
        exc_service.add_exception(
            global_cal.id,
            exception_date=date(2026, 1, 1),
            exception_type="BOGUS",
            name="X",
            impact_type=ImpactType.UNAVAILABLE.value,
        )


def test_exception_list_by_calendar(exc_service, global_cal):
    exc_service.add_exception(
        global_cal.id,
        exception_date=date(2026, 1, 1),
        exception_type=ExceptionType.HOLIDAY.value,
        name="New Year",
        impact_type=ImpactType.UNAVAILABLE.value,
    )
    exc_service.add_exception(
        global_cal.id,
        exception_date=date(2026, 12, 25),
        exception_type=ExceptionType.HOLIDAY.value,
        name="Christmas",
        impact_type=ImpactType.UNAVAILABLE.value,
    )
    exceptions = exc_service.list_exceptions(global_cal.id)
    assert len(exceptions) == 2


def test_exception_delete(exc_service, global_cal):
    exc = exc_service.add_exception(
        global_cal.id,
        exception_date=date(2026, 6, 15),
        exception_type=ExceptionType.SHUTDOWN.value,
        name="Site Shutdown",
        impact_type=ImpactType.UNAVAILABLE.value,
    )
    exc_service.delete_exception(exc.id)
    exceptions = exc_service.list_exceptions(global_cal.id)
    assert all(e.id != exc.id for e in exceptions)


# ---------------------------------------------------------------------------
# Tests — Recurring Events
# ---------------------------------------------------------------------------


def test_recurring_event_rrule_expanded(recurring_service, global_cal):
    event = recurring_service.add_recurring_event(
        global_cal.id,
        title="Weekly Standup",
        event_type=RecurringEventType.MEETING.value,
        recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
        start_time=time(9, 0),
        end_time=time(9, 30),
        impact_type=ImpactType.REDUCED_CAPACITY.value,
        effective_from=date(2026, 6, 1),
    )
    occurrences = recurring_service.expand_occurrences(
        event.id,
        date(2026, 6, 1),
        date(2026, 6, 30),
    )
    assert len(occurrences) >= 4  # 4 Mondays in June 2026
    assert all(d.weekday() == 0 for d in occurrences)  # all Mondays


def test_recurring_event_invalid_rrule_raises(recurring_service, global_cal):
    with pytest.raises(ValidationError, match="Invalid recurrence_rule"):
        recurring_service.add_recurring_event(
            global_cal.id,
            title="Bad",
            event_type=RecurringEventType.MEETING.value,
            recurrence_rule="THIS IS NOT A RRULE",
            start_time=time(9, 0),
            end_time=time(10, 0),
            impact_type=ImpactType.UNAVAILABLE.value,
            effective_from=date(2026, 1, 1),
        )


def test_recurring_event_delete(recurring_service, global_cal):
    event = recurring_service.add_recurring_event(
        global_cal.id,
        title="Weekly Cleanup",
        event_type=RecurringEventType.ADMIN.value,
        recurrence_rule="FREQ=WEEKLY;BYDAY=FR",
        start_time=time(17, 0),
        end_time=time(18, 0),
        impact_type=ImpactType.INFORMATION_ONLY.value,
        effective_from=date(2026, 1, 1),
    )
    recurring_service.delete_recurring_event(event.id)
    events = recurring_service.list_recurring_events(global_cal.id)
    assert all(e.id != event.id for e in events)


# ---------------------------------------------------------------------------
# Tests — Shift Patterns
# ---------------------------------------------------------------------------


def test_shift_pattern_created(shift_service):
    pattern = shift_service.create_shift_pattern(
        code="STD-8H",
        name="Standard 8h",
        pattern_type=PatternType.STANDARD.value,
        timezone="UTC",
    )
    assert pattern.code == "STD-8H"
    assert pattern.pattern_type == PatternType.STANDARD.value


def test_shift_pattern_days_created(shift_service):
    pattern = shift_service.create_shift_pattern(
        code="DAY-NIGHT",
        name="Day/Night Rotation",
        pattern_type=PatternType.TWO_SHIFT.value,
        rotation_cycle_days=2,
    )
    day0 = shift_service.set_day(
        pattern.id,
        day_offset=0,
        is_working_day=True,
        start_time=time(6, 0),
        end_time=time(14, 0),
        shift_label="Day",
    )
    day1 = shift_service.set_day(
        pattern.id,
        day_offset=1,
        is_working_day=True,
        start_time=time(14, 0),
        end_time=time(22, 0),
        shift_label="Night",
    )
    days = shift_service.list_days(pattern.id)
    assert len(days) == 2
    assert days[0].shift_label == "Day"
    assert days[1].shift_label == "Night"


def test_shift_pattern_duplicate_code_raises(shift_service):
    shift_service.create_shift_pattern(
        code="UNIQUE", name="X", pattern_type=PatternType.STANDARD.value
    )
    with pytest.raises(ValidationError, match="already exists"):
        shift_service.create_shift_pattern(
            code="UNIQUE", name="Y", pattern_type=PatternType.STANDARD.value
        )


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
    a = assignment_service.assign_department_calendar("dept-eng", global_cal.id)
    fetched = assignment_service.get_department_calendar("dept-eng")
    assert fetched is not None
    assert fetched.department_id == "dept-eng"


def test_employee_calendar_assignment(assignment_service, global_cal):
    a = assignment_service.assign_employee_calendar("emp-jsmith", global_cal.id)
    fetched = assignment_service.get_employee_calendar("emp-jsmith")
    assert fetched is not None
    assert fetched.employee_id == "emp-jsmith"


def test_assignment_removal(assignment_service, global_cal):
    a = assignment_service.assign_site_calendar("site-x", global_cal.id)
    assignment_service.remove_site_assignment(a.id)
    fetched = assignment_service.get_site_calendar("site-x")
    assert fetched is None


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


# ---------------------------------------------------------------------------
# Tests — EnterpriseCalendarResolver
# ---------------------------------------------------------------------------


def test_resolver_returns_unavailable_with_no_global_calendar(resolver):
    # No calendars or rules set up → no working rules → not working
    ctx = resolver.resolve_calendar_context(target_date=date(2026, 6, 1))
    assert ctx.available_hours == 0.0  # no rules means no working hours
    assert ctx.source_chain == []


def test_resolver_source_chain_global(
    resolver, repos, global_cal, rule_service, org_id
):
    rule_service.seed_standard_week(
        global_cal.id,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
    )
    ctx = resolver.resolve_calendar_context(target_date=date(2026, 6, 1))
    assert "GLOBAL" in ctx.source_chain
    assert ctx.base_hours == 8.0
    assert ctx.available_hours == 8.0


def test_resolver_site_overrides_global(
    resolver, repos, global_cal, rule_service, assignment_service, cal_service, org_id
):
    rule_service.seed_standard_week(
        global_cal.id,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
    )
    site_cal = cal_service.create_calendar(
        code="SITE-HH",
        name="Hamburg",
        calendar_type=CalendarType.SITE.value,
        timezone="Europe/Berlin",
    )
    rule_service.save_rule(
        site_cal.id,
        weekday=0,  # Monday
        is_working_day=True,
        start_time=time(7, 0),
        end_time=time(15, 0),
        break_minutes=30,
        hours_override=7.5,
    )
    assignment_service.assign_site_calendar("site-hamburg", site_cal.id)

    ctx = resolver.resolve_calendar_context(
        site_id="site-hamburg",
        target_date=date(2026, 6, 1),  # Monday
    )
    assert "GLOBAL" in ctx.source_chain
    assert any("SITE" in s for s in ctx.source_chain)
    assert ctx.base_hours == 7.5  # site overrides global


def test_resolver_holiday_exception_from_global(
    resolver, global_cal, rule_service, exc_service
):
    rule_service.seed_standard_week(
        global_cal.id,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
    )
    exc_service.add_exception(
        global_cal.id,
        exception_date=date(2026, 6, 1),
        exception_type=ExceptionType.HOLIDAY.value,
        name="Global Holiday",
        impact_type=ImpactType.UNAVAILABLE.value,
    )
    ctx = resolver.resolve_calendar_context(target_date=date(2026, 6, 1))
    assert ctx.available_hours == 0.0
    assert ctx.status == "UNAVAILABLE"


def test_granularity_validation_rejected():
    from src.core.platform.calendar.application.enterprise_calendar_service import (
        _VALID_GRANULARITIES,
    )
    assert 5 in _VALID_GRANULARITIES
    assert 15 in _VALID_GRANULARITIES
    assert 7 not in _VALID_GRANULARITIES
