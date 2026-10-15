from __future__ import annotations

from datetime import UTC, date, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds
from src.core.platform.application.time_management.calendar.assignment.commands.calendar_assignment_commands import (
    CalendarAssignmentCommandHandler,
)
from src.core.platform.application.time_management.calendar.assignment.dto.commands.calendar_assignments import (
    SiteCalendarAssignCommand,
)
from src.core.platform.application.time_management.calendar.assignment.queries.calendar_assignment_queries import (
    CalendarAssignmentQueryHandler,
)
from src.core.platform.application.time_management.calendar.capacity.dto.queries.calendar_resolution import (
    ResolveCalendarRangeCommand,
    ResolveContextCommand,
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
from src.core.platform.application.time_management.calendar.definitions.dto.commands.calendar_exceptions import (
    ExceptionCreateCommand,
)
from src.core.platform.application.time_management.calendar.definitions.dto.commands.recurring_events import (
    RecurringEventCreateCommand,
)
from src.core.platform.application.time_management.calendar.definitions.dto.commands.working_rules import (
    WorkingRuleSaveCommand,
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
from src.core.platform.application.time_management.calendar.dto.commands.calendars import (
    CalendarCreateCommand,
)
from src.core.platform.application.time_management.calendar.queries.platform_calendar_queries import (
    PlatformCalendarQueryHandler,
)
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
def seeded_assignment_entities(db_session, org_id):
    from datetime import datetime

    from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import (
        SiteORM,
    )

    now = datetime.now(UTC)
    db_session.add_all(
        [
            SiteORM(
                id=site_id,
                tenant_id="tenant-platform-foundation",
                organization_id=org_id,
                site_code=site_id,
                name=site_id,
                created_at=now,
                updated_at=now,
            )
            for site_id in ("site-hamburg",)
        ]
    )
    db_session.flush()


@pytest.fixture
def assignment_commands(
    db_session, repos, mock_user_session, seeded_assignment_entities
):
    from unittest.mock import MagicMock

    pm_proj_repo = MagicMock()
    pm_proj_repo.save.return_value = None
    pm_proj_repo.get.return_value = None
    pm_proj_repo.list_for_calendar.return_value = []
    pm_res_repo = MagicMock()
    pm_res_repo.save.return_value = None
    pm_res_repo.get.return_value = None
    pm_res_repo.list_for_calendar.return_value = []
    return CalendarAssignmentCommandHandler(
        session=db_session,
        calendar_repo=repos["calendar"],
        assignment_repo=repos["assignment"],
        project_assignment_repo=pm_proj_repo,
        resource_assignment_repo=pm_res_repo,
        user_session=mock_user_session,
    )


@pytest.fixture
def assignment_queries(
    db_session, repos, mock_user_session, seeded_assignment_entities
):
    from unittest.mock import MagicMock

    pm_proj_repo = MagicMock()
    pm_proj_repo.save.return_value = None
    pm_proj_repo.get.return_value = None
    pm_proj_repo.list_for_calendar.return_value = []
    pm_res_repo = MagicMock()
    pm_res_repo.save.return_value = None
    pm_res_repo.get.return_value = None
    pm_res_repo.list_for_calendar.return_value = []
    return CalendarAssignmentQueryHandler(
        assignment_repo=repos["assignment"],
        project_assignment_repo=pm_proj_repo,
        resource_assignment_repo=pm_res_repo,
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
    return PlatformCalendarResolver(
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
def global_cal(cal_commands, org_id):
    return cal_commands.ensure_global_calendar(org_id)


# ---------------------------------------------------------------------------
# Tests — PlatformCalendarResolver
# ---------------------------------------------------------------------------


def test_resolver_returns_unavailable_with_no_global_calendar(resolver):
    ctx = resolver.resolve_calendar_context(
        ResolveContextCommand(target_date=date(2026, 6, 1))
    )
    assert ctx.available_hours == 0.0  # no rules means no working hours
    assert ctx.source_chain == []


def test_resolver_warns_once_per_scope_not_once_per_date(resolver, caplog):
    """A day-by-day caller (e.g. ProjectCalendarAdapter.add_working_days
    walking backward/forward searching for a working day) can call
    resolve_calendar_context hundreds of times for the SAME missing-chain
    project/resource -- this must log the "no source chain" warning once
    per distinct scope, not once per date, or a single call floods the log
    with one line per day (observed: hundreds of lines for one real
    add_working_days call on a project with no calendar configured)."""
    import logging

    with caplog.at_level(logging.WARNING):
        for day in range(1, 15):
            resolver.resolve_calendar_context(
                ResolveContextCommand(
                    project_id="proj-without-a-calendar", target_date=date(2026, 1, day)
                )
            )

    no_chain_records = [
        r for r in caplog.records if "resolved without source chain" in r.message
    ]
    assert len(no_chain_records) == 1, (
        f"expected exactly one dedup'd warning for 14 calls on the same "
        f"scope, got {len(no_chain_records)}"
    )

    # A DIFFERENT scope must still get its own warning -- dedup is per-scope,
    # not global.
    with caplog.at_level(logging.WARNING):
        resolver.resolve_calendar_context(
            ResolveContextCommand(
                project_id="a-different-project-without-a-calendar",
                target_date=date(2026, 1, 1),
            )
        )
    no_chain_records = [
        r for r in caplog.records if "resolved without source chain" in r.message
    ]
    assert len(no_chain_records) == 2


def test_resolver_source_chain_global(
    resolver, repos, global_cal, rule_commands, org_id
):
    rule_commands.seed_standard_week(
        global_cal.id,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
    )
    ctx = resolver.resolve_calendar_context(
        ResolveContextCommand(target_date=date(2026, 6, 1))
    )
    assert "GLOBAL" in ctx.source_chain
    assert ctx.base_hours == 8.0
    assert ctx.available_hours == 8.0


def test_resolver_site_overrides_global(
    resolver,
    repos,
    global_cal,
    rule_commands,
    assignment_commands,
    cal_commands,
    org_id,
):
    rule_commands.seed_standard_week(
        global_cal.id,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
    )
    site_cal = cal_commands.create_calendar(
        CalendarCreateCommand(
            code="SITE-HH",
            name="Hamburg",
            calendar_type=CalendarType.SITE.value,
            timezone="Europe/Berlin",
        )
    )
    rule_commands.save_rule(
        WorkingRuleSaveCommand(
            calendar_id=site_cal.id,
            weekday=0,
            is_working_day=True,
            start_time=time(7, 0),
            end_time=time(15, 0),
            break_minutes=30,
            hours_override=7.5,
        )
    )
    assignment_commands.assign_site_calendar(
        SiteCalendarAssignCommand(site_id="site-hamburg", calendar_id=site_cal.id)
    )

    ctx = resolver.resolve_calendar_context(
        ResolveContextCommand(site_id="site-hamburg", target_date=date(2026, 6, 1))
    )
    assert "GLOBAL" in ctx.source_chain
    assert any("SITE" in s for s in ctx.source_chain)
    assert ctx.base_hours == 7.5  # site overrides global


def test_resolver_holiday_exception_from_global(
    resolver, global_cal, rule_commands, exc_commands
):
    rule_commands.seed_standard_week(
        global_cal.id,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
    )
    exc_commands.add_exception(
        ExceptionCreateCommand(
            calendar_id=global_cal.id,
            exception_date=date(2026, 6, 1),
            exception_type=ExceptionType.HOLIDAY.value,
            name="Global Holiday",
            impact_type=ImpactType.UNAVAILABLE.value,
        )
    )
    ctx = resolver.resolve_calendar_context(
        ResolveContextCommand(target_date=date(2026, 6, 1))
    )
    assert ctx.available_hours == 0.0
    assert ctx.status == "UNAVAILABLE"


def test_resolver_surfaces_recurring_event_on_a_matching_day(
    resolver, global_cal, rule_commands, recurring_commands
):
    """Regression guard: a recurring event with no CalendarException row
    must still be visible on the resolved day context (name/type/impact),
    not just reflected as an unexplained hours delta -- this is what the
    Month view reads to show *why* a day's hours changed."""
    rule_commands.seed_standard_week(
        global_cal.id,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
    )
    recurring_commands.add_recurring_event(
        RecurringEventCreateCommand(
            calendar_id=global_cal.id,
            title="Weekly Standup",
            event_type=RecurringEventType.MEETING.value,
            recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
            start_time=time(9, 0),
            end_time=time(9, 30),
            impact_type=ImpactType.REDUCED_CAPACITY.value,
            effective_from=date(2026, 6, 1),
        )
    )

    monday_ctx = resolver.resolve_calendar_context(
        ResolveContextCommand(target_date=date(2026, 6, 1))
    )  # Monday
    assert monday_ctx.available_hours == 7.5  # 8h - 0.5h meeting
    assert len(monday_ctx.recurring_events) == 1
    assert monday_ctx.recurring_events[0]["name"] == "Weekly Standup"
    assert monday_ctx.recurring_events[0]["type"] == RecurringEventType.MEETING.value
    assert monday_ctx.recurring_events[0]["impact"] == ImpactType.REDUCED_CAPACITY.value

    tuesday_ctx = resolver.resolve_calendar_context(
        ResolveContextCommand(target_date=date(2026, 6, 2))
    )  # Tuesday
    assert tuesday_ctx.available_hours == 8.0
    assert tuesday_ctx.recurring_events == []


def test_resolve_range_surfaces_recurring_events_per_day(
    resolver, global_cal, rule_commands, recurring_commands
):
    rule_commands.seed_standard_week(
        global_cal.id,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes=60,
    )
    recurring_commands.add_recurring_event(
        RecurringEventCreateCommand(
            calendar_id=global_cal.id,
            title="Weekly Standup",
            event_type=RecurringEventType.MEETING.value,
            recurrence_rule="FREQ=WEEKLY;BYDAY=MO",
            start_time=time(9, 0),
            end_time=time(9, 30),
            impact_type=ImpactType.REDUCED_CAPACITY.value,
            effective_from=date(2026, 6, 1),
        )
    )

    days = resolver.resolve_range(
        ResolveCalendarRangeCommand(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 7)
        )
    )
    mondays = [d for d in days if d.date.weekday() == 0]
    assert len(mondays) == 1
    assert mondays[0].recurring_events[0]["name"] == "Weekly Standup"
    non_mondays = [d for d in days if d.date.weekday() != 0]
    assert all(d.recurring_events == [] for d in non_mondays)


def test_granularity_validation_rejected():
    from src.core.platform.application.time_management.calendar.commands.platform_calendar_commands import (
        _VALID_GRANULARITIES,
    )

    assert 5 in _VALID_GRANULARITIES
    assert 15 in _VALID_GRANULARITIES
    assert 7 not in _VALID_GRANULARITIES


# ---------------------------------------------------------------------------
# Tests — PlatformCalendarResolver.business_today
# ---------------------------------------------------------------------------


def test_resolver_business_today_matches_shared_helper_for_the_default_utc_calendar(
    resolver, global_cal
):
    """ensure_global_calendar seeds UTC when the organization has no
    configured timezone -- business_today() must resolve against that
    calendar's actual timezone, not a hardcoded assumption."""
    from src.core.shared.time.business_date import (
        business_today as shared_business_today,
    )

    assert resolver.business_today() == shared_business_today(global_cal.timezone)


def test_resolver_business_today_falls_back_to_utc_when_no_global_calendar_exists(
    resolver,
):
    from src.core.shared.time.business_date import (
        business_today as shared_business_today,
    )

    assert resolver.business_today() == shared_business_today(None)


def test_resolver_business_today_honors_a_non_utc_organization_timezone(
    resolver, repos, global_cal, monkeypatch
):
    """A server running in UTC must not treat midnight UTC as the day
    boundary for an organization configured in a different timezone."""
    from dataclasses import replace
    from datetime import datetime

    import src.core.platform.application.time_management.calendar.capacity.platform_calendar_resolver as resolver_module
    from src.core.shared.time.business_date import (
        business_today as shared_business_today,
    )

    moved = replace(global_cal, timezone="Pacific/Auckland")
    repos["calendar"].update(moved)

    # 23:30 UTC is already the next calendar day in Pacific/Auckland (UTC+13).
    fixed_now = datetime(2026, 1, 1, 23, 30, tzinfo=UTC)
    monkeypatch.setattr(
        resolver_module,
        "business_today",
        lambda tz_name: shared_business_today(tz_name, now=fixed_now),
    )

    assert resolver.business_today() == date(2026, 1, 2)
