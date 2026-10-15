from __future__ import annotations

from datetime import date, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds
from src.core.platform.application.time_management.calendar.commands.platform_calendar_commands import (
    PlatformCalendarCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.calendar_exception_commands import (
    CalendarExceptionCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.recurring_event_commands import (
    RecurringEventCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.shift_pattern_commands import (
    ShiftPatternCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.calendar_exception_queries import (
    CalendarExceptionQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.recurring_event_queries import (
    RecurringEventQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.shift_pattern_queries import (
    ShiftPatternQueryHandler,
)
from src.core.platform.application.time_management.calendar.queries.platform_calendar_queries import (
    PlatformCalendarQueryHandler,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    ExceptionType,
    ImpactType,
    PatternType,
    RecurringEventType,
)
from src.core.platform.infrastructure.persistence.repositories.time_management.calendar.enterprise_calendar import (
    SqlAlchemyCalendarAssignmentRepository,
    SqlAlchemyCalendarExceptionRepository,
    SqlAlchemyCalendarRecurringEventRepository,
    SqlAlchemyCalendarWorkingRuleRepository,
    SqlAlchemyPlatformCalendarRepository,
    SqlAlchemyShiftPatternRepository,
)
from src.infra.persistence.orm import Base


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
    from dataclasses import dataclass
    from unittest.mock import MagicMock

    @dataclass
    class FakeOrg:
        id: str = org_id

    repo = MagicMock()
    repo.get_active.return_value = FakeOrg()
    return repo


@pytest.fixture
def tenant_context(org_id):
    from dataclasses import dataclass
    from unittest.mock import MagicMock

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
    context.require_active_scope_ids.return_value = ActiveScopeIds(
        tenant_id="tenant-platform-foundation", organization_id=org_id
    )
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
        "shift": SqlAlchemyShiftPatternRepository(db_session),
        "assignment": SqlAlchemyCalendarAssignmentRepository(db_session),
    }
    for repo in repos.values():
        if hasattr(repo, "_tenant_context_service"):
            repo._tenant_context_service = tenant_context
    return repos


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
def shift_commands(db_session, repos, mock_org_repo, mock_user_session, tenant_context):
    return ShiftPatternCommandHandler(
        session=db_session,
        pattern_repo=repos["shift"],
        user_session=mock_user_session,
        tenant_context_service=tenant_context,
    )


@pytest.fixture
def shift_queries(db_session, repos, mock_org_repo, mock_user_session, tenant_context):
    return ShiftPatternQueryHandler(
        pattern_repo=repos["shift"],
        user_session=mock_user_session,
        tenant_context_service=tenant_context,
    )


@pytest.fixture
def global_cal(cal_commands, org_id):
    return cal_commands.ensure_global_calendar(org_id)


# ---------------------------------------------------------------------------
# Tests — Exceptions
# ---------------------------------------------------------------------------


def test_exception_types_persist_correctly(exc_commands, global_cal):
    exc = exc_commands.add_exception(
        global_cal.id,
        exception_date=date(2026, 12, 25),
        exception_type=ExceptionType.HOLIDAY.value,
        name="Christmas",
        impact_type=ImpactType.UNAVAILABLE.value,
    )
    assert exc.exception_type == ExceptionType.HOLIDAY.value
    assert exc.impact_type == ImpactType.UNAVAILABLE.value
    assert exc.exception_date == date(2026, 12, 25)


def test_exception_invalid_type_raises(exc_commands, global_cal):
    with pytest.raises(ValidationError, match="Invalid exception_type"):
        exc_commands.add_exception(
            global_cal.id,
            exception_date=date(2026, 1, 1),
            exception_type="BOGUS",
            name="X",
            impact_type=ImpactType.UNAVAILABLE.value,
        )


def test_exception_list_by_calendar(exc_queries, exc_commands, global_cal):
    exc_commands.add_exception(
        global_cal.id,
        exception_date=date(2026, 1, 1),
        exception_type=ExceptionType.HOLIDAY.value,
        name="New Year",
        impact_type=ImpactType.UNAVAILABLE.value,
    )
    exc_commands.add_exception(
        global_cal.id,
        exception_date=date(2026, 12, 25),
        exception_type=ExceptionType.HOLIDAY.value,
        name="Christmas",
        impact_type=ImpactType.UNAVAILABLE.value,
    )
    exceptions = exc_queries.list_exceptions(global_cal.id)
    assert len(exceptions) == 2


def test_exception_delete(exc_queries, exc_commands, global_cal):
    exc = exc_commands.add_exception(
        global_cal.id,
        exception_date=date(2026, 6, 15),
        exception_type=ExceptionType.SHUTDOWN.value,
        name="Site Shutdown",
        impact_type=ImpactType.UNAVAILABLE.value,
    )
    exc_commands.delete_exception(exc.id)
    exceptions = exc_queries.list_exceptions(global_cal.id)
    assert all(e.id != exc.id for e in exceptions)


# ---------------------------------------------------------------------------
# Tests — Recurring Events
# ---------------------------------------------------------------------------


def test_recurring_event_rrule_expanded(
    recurring_queries, recurring_commands, global_cal
):
    event = recurring_commands.add_recurring_event(
        global_cal.id,
        title="Weekly Standup",
        event_type=RecurringEventType.MEETING.value,
        recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
        start_time=time(9, 0),
        end_time=time(9, 30),
        impact_type=ImpactType.REDUCED_CAPACITY.value,
        effective_from=date(2026, 6, 1),
    )
    occurrences = recurring_queries.expand_occurrences(
        event.id,
        date(2026, 6, 1),
        date(2026, 6, 30),
    )
    assert len(occurrences) >= 4  # 4 Mondays in June 2026
    assert all(d.weekday() == 0 for d in occurrences)  # all Mondays


def test_recurring_event_invalid_rrule_raises(recurring_commands, global_cal):
    with pytest.raises(ValidationError, match="Invalid recurrence_rule"):
        recurring_commands.add_recurring_event(
            global_cal.id,
            title="Bad",
            event_type=RecurringEventType.MEETING.value,
            recurrence_rule="THIS IS NOT A RRULE",
            start_time=time(9, 0),
            end_time=time(10, 0),
            impact_type=ImpactType.UNAVAILABLE.value,
            effective_from=date(2026, 1, 1),
        )


def test_recurring_event_delete(recurring_queries, recurring_commands, global_cal):
    event = recurring_commands.add_recurring_event(
        global_cal.id,
        title="Weekly Cleanup",
        event_type=RecurringEventType.ADMIN.value,
        recurrence_rule="FREQ=WEEKLY;BYDAY=FR",
        start_time=time(17, 0),
        end_time=time(18, 0),
        impact_type=ImpactType.INFORMATION_ONLY.value,
        effective_from=date(2026, 1, 1),
    )
    recurring_commands.delete_recurring_event(event.id)
    events = recurring_queries.list_recurring_events(global_cal.id)
    assert all(e.id != event.id for e in events)


def test_recurring_event_repository_page_is_bounded_and_filtered(
    recurring_commands, repos, global_cal
):
    for title, event_type in (
        ("Alpha Meeting", RecurringEventType.MEETING.value),
        ("Beta Meeting", RecurringEventType.MEETING.value),
        ("Gamma Admin", RecurringEventType.ADMIN.value),
    ):
        recurring_commands.add_recurring_event(
            global_cal.id,
            title=title,
            event_type=event_type,
            recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
            start_time=time(9, 0),
            end_time=time(10, 0),
            impact_type=ImpactType.INFORMATION_ONLY.value,
            effective_from=date(2026, 1, 1),
        )

    first, total, filtered_total = repos["recurring"].list_page_for_calendar(
        global_cal.id, page=1, page_size=1, search="Meeting"
    )
    second, _, _ = repos["recurring"].list_page_for_calendar(
        global_cal.id, page=2, page_size=1, search="Meeting"
    )
    assert (total, filtered_total) == (3, 2)
    assert [event.title for event in first] == ["Alpha Meeting"]
    assert [event.title for event in second] == ["Beta Meeting"]


# ---------------------------------------------------------------------------
# Tests — Shift Patterns
# ---------------------------------------------------------------------------


def test_shift_pattern_created(shift_commands):
    pattern = shift_commands.create_shift_pattern(
        code="STD-8H",
        name="Standard 8h",
        pattern_type=PatternType.STANDARD.value,
        timezone="UTC",
    )
    assert pattern.code == "STD-8H"
    assert pattern.pattern_type == PatternType.STANDARD.value


def test_shift_pattern_days_created(shift_queries, shift_commands):
    pattern = shift_commands.create_shift_pattern(
        code="DAY-NIGHT",
        name="Day/Night Rotation",
        pattern_type=PatternType.TWO_SHIFT.value,
        rotation_cycle_days=2,
    )
    shift_commands.set_day(
        pattern.id,
        day_offset=0,
        is_working_day=True,
        start_time=time(6, 0),
        end_time=time(14, 0),
        shift_label="Day",
    )
    shift_commands.set_day(
        pattern.id,
        day_offset=1,
        is_working_day=True,
        start_time=time(14, 0),
        end_time=time(22, 0),
        shift_label="Night",
    )
    days = shift_queries.list_days(pattern.id)
    assert len(days) == 2
    assert days[0].shift_label == "Day"
    assert days[1].shift_label == "Night"


def test_shift_pattern_duplicate_code_raises(shift_commands):
    shift_commands.create_shift_pattern(
        code="UNIQUE", name="X", pattern_type=PatternType.STANDARD.value
    )
    with pytest.raises(ValidationError, match="already exists"):
        shift_commands.create_shift_pattern(
            code="UNIQUE", name="Y", pattern_type=PatternType.STANDARD.value
        )
