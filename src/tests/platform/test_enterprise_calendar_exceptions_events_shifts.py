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
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    CalendarType,
    ExceptionType,
    ImpactType,
    PatternType,
    RecurringEventType,
)
from src.core.platform.application.time_management.calendar.enterprise_calendar_service import (
    EnterpriseCalendarService,
)
from src.core.platform.application.time_management.calendar.definitions.calendar_exception_service import (
    CalendarExceptionService,
)
from src.core.platform.application.time_management.calendar.definitions.recurring_event_service import RecurringEventService
from src.core.platform.application.time_management.calendar.definitions.shift_pattern_service import ShiftPatternService
from src.core.platform.common.exceptions import ValidationError


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
def global_cal(cal_service, org_id):
    return cal_service.ensure_global_calendar(org_id)


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
    shift_service.set_day(
        pattern.id,
        day_offset=0,
        is_working_day=True,
        start_time=time(6, 0),
        end_time=time(14, 0),
        shift_label="Day",
    )
    shift_service.set_day(
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
