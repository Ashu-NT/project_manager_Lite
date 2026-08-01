"""Verifies ShiftPattern/ShiftPatternDay are actually consulted by the
enterprise calendar resolver — a rotation pattern's day-in-cycle overrides
the weekday-based working rule, in both the single-day and bulk-range
resolution paths."""

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
from src.core.platform.calendar.application.enterprise_calendar_service import (
    EnterpriseCalendarService,
)
from src.core.platform.calendar.application.working_rule_service import WorkingRuleService
from src.core.platform.calendar.application.shift_pattern_service import ShiftPatternService
from src.core.platform.calendar.application.enterprise_calendar_resolver import (
    EnterpriseCalendarResolver,
)
from src.core.platform.calendar.application.working_time_calculator import WorkingTimeCalculator
from src.core.platform.calendar.domain.enterprise_calendar import PatternType


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
    return "org-shift-pattern"


@pytest.fixture
def tenant_context(org_id):
    from unittest.mock import MagicMock
    from dataclasses import dataclass

    @dataclass
    class FakeOrg:
        id: str = org_id

    @dataclass
    class FakeContext:
        tenant_id: str = "tenant-shift-pattern"
        organization_id: str = org_id
        organization: FakeOrg | None = None

    context = MagicMock()
    context.require_active_organization_id.return_value = org_id
    context.get_active_organization_id.return_value = org_id
    context.get_active_organization.return_value = FakeOrg()
    context.get_active_tenant_id.return_value = "tenant-shift-pattern"
    context.require_organization_context.return_value = FakeContext(organization=FakeOrg())
    return context


@pytest.fixture
def mock_user_session():
    from unittest.mock import MagicMock
    session = MagicMock()
    session.has_permission.return_value = True
    session.username = "test-admin"
    return session


@pytest.fixture
def mock_org_repo(org_id):
    from unittest.mock import MagicMock
    from dataclasses import dataclass

    @dataclass
    class FakeOrg:
        id: str = org_id

    repo = MagicMock()
    repo.get_active.return_value = FakeOrg()
    return repo


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
def rule_service(db_session, repos, mock_user_session):
    return WorkingRuleService(
        session=db_session,
        calendar_repo=repos["calendar"],
        rule_repo=repos["rule"],
        user_session=mock_user_session,
    )


@pytest.fixture
def shift_pattern_service(db_session, repos, mock_org_repo, mock_user_session, tenant_context):
    return ShiftPatternService(
        session=db_session,
        pattern_repo=repos["shift"],
        organization_repo=mock_org_repo,
        user_session=mock_user_session,
        tenant_context_service=tenant_context,
    )


@pytest.fixture
def resolver(repos, org_id):
    from unittest.mock import MagicMock
    return EnterpriseCalendarResolver(
        organization_id=org_id,
        calendar_repo=repos["calendar"],
        rule_repo=repos["rule"],
        exception_repo=repos["exception"],
        recurring_repo=repos["recurring"],
        assignment_repo=repos["assignment"],
        project_assignment_repo=MagicMock(),
        resource_assignment_repo=MagicMock(),
        calculator=WorkingTimeCalculator(),
        shift_pattern_repo=repos["shift"],
    )


@pytest.fixture
def rotating_global_calendar(cal_service, rule_service, shift_pattern_service, org_id):
    """Global calendar where every weekday rule points at a 2-on/2-off
    rotation pattern anchored on Monday 2026-06-01, 12h shifts."""
    global_cal = cal_service.ensure_global_calendar(org_id)
    for weekday in range(7):
        rule_service.save_rule(
            global_cal.id,
            weekday=weekday,
            is_working_day=True,
            shift_code="ROT-A",
        )

    pattern = shift_pattern_service.create_shift_pattern(
        code="ROT-A",
        name="2-on 2-off Rotation",
        pattern_type=PatternType.ROTATING.value,
        rotation_cycle_days=4,
        anchor_date=date(2026, 6, 1),
    )
    shift_pattern_service.set_day(pattern.id, 0, is_working_day=True, hours=12.0)
    shift_pattern_service.set_day(pattern.id, 1, is_working_day=True, hours=12.0)
    shift_pattern_service.set_day(pattern.id, 2, is_working_day=False)
    shift_pattern_service.set_day(pattern.id, 3, is_working_day=False)

    return global_cal


def test_shift_pattern_overrides_weekday_rule_single_day(resolver, rotating_global_calendar):
    # Anchor Monday 2026-06-01 = offset 0 = 12h working, overriding the
    # weekday rule (which would otherwise use the default 8h fallback).
    ctx = resolver.resolve_calendar_context(target_date=date(2026, 6, 1))
    assert ctx.available_hours == 12.0

    # 2026-06-03 (Wednesday) = offset 2 = day off, even though it's a
    # normal weekday with a shift_code-bearing working rule.
    ctx_off = resolver.resolve_calendar_context(target_date=date(2026, 6, 3))
    assert ctx_off.available_hours == 0.0

    # 2026-06-05 (Friday) = (June5 - June1).days % 4 = 0 = 12h working —
    # proves the rotation, not the weekday, determines the schedule.
    ctx_friday = resolver.resolve_calendar_context(target_date=date(2026, 6, 5))
    assert ctx_friday.available_hours == 12.0


def test_shift_pattern_overrides_weekday_rule_in_bulk_range(resolver, rotating_global_calendar):
    results = resolver.resolve_range(start=date(2026, 6, 1), end=date(2026, 6, 5))
    available_by_date = {r.date: r.available_hours for r in results}
    assert available_by_date[date(2026, 6, 1)] == 12.0  # Mon, offset 0
    assert available_by_date[date(2026, 6, 2)] == 12.0  # Tue, offset 1
    assert available_by_date[date(2026, 6, 3)] == 0.0   # Wed, offset 2 (off)
    assert available_by_date[date(2026, 6, 4)] == 0.0   # Thu, offset 3 (off)
    assert available_by_date[date(2026, 6, 5)] == 12.0  # Fri, offset 0 again


def test_desktop_api_can_set_and_delete_shift_pattern_days(
    db_session, repos, mock_org_repo, mock_user_session, tenant_context, shift_pattern_service
):
    from unittest.mock import MagicMock
    from src.api.desktop.platform.enterprise_calendar import EnterpriseCalendarDesktopApi
    from src.api.desktop.platform.models.enterprise_calendar import (
        ShiftPatternCreateCommand,
        ShiftPatternDaySetCommand,
    )
    from src.core.platform.calendar.application.enterprise_calendar_service import (
        EnterpriseCalendarService,
    )
    from src.core.platform.calendar.application.calendar_assignment_service import (
        CalendarAssignmentService,
    )
    from src.core.platform.calendar.application.enterprise_calendar_resolver import (
        EnterpriseCalendarResolver,
    )
    from src.core.platform.calendar.application.working_time_calculator import (
        WorkingTimeCalculator,
    )

    cal_service = EnterpriseCalendarService(
        session=db_session,
        calendar_repo=repos["calendar"],
        assignment_repo=repos["assignment"],
        organization_repo=mock_org_repo,
        user_session=mock_user_session,
        tenant_context_service=tenant_context,
    )
    assignment_service = CalendarAssignmentService(
        session=db_session,
        calendar_repo=repos["calendar"],
        assignment_repo=repos["assignment"],
        project_assignment_repo=MagicMock(),
        resource_assignment_repo=MagicMock(),
        user_session=mock_user_session,
    )
    resolver = EnterpriseCalendarResolver(
        organization_id="org-shift-pattern",
        calendar_repo=repos["calendar"],
        rule_repo=repos["rule"],
        exception_repo=repos["exception"],
        recurring_repo=repos["recurring"],
        assignment_repo=repos["assignment"],
        project_assignment_repo=MagicMock(),
        resource_assignment_repo=MagicMock(),
        calculator=WorkingTimeCalculator(),
        shift_pattern_repo=repos["shift"],
    )
    api = EnterpriseCalendarDesktopApi(
        calendar_service=cal_service,
        rule_service=MagicMock(),
        exception_service=MagicMock(),
        recurring_event_service=MagicMock(),
        shift_pattern_service=shift_pattern_service,
        assignment_service=assignment_service,
        resolver=resolver,
    )

    created = api.create_shift_pattern(
        ShiftPatternCreateCommand(
            code="ROT-B",
            name="Rotation B",
            pattern_type="ROTATING",
            rotation_cycle_days=2,
            anchor_date="2026-06-01",
        )
    )
    assert created.ok is True
    assert created.data.anchor_date == "2026-06-01"

    day_result = api.set_shift_pattern_day(
        ShiftPatternDaySetCommand(
            pattern_id=created.data.id,
            day_offset=0,
            is_working_day=True,
            hours=12.0,
        )
    )
    assert day_result.ok is True
    assert day_result.data.hours == 12.0

    days_result = api.list_shift_pattern_days(created.data.id)
    assert len(days_result.data) == 1

    delete_result = api.delete_shift_pattern_day(day_result.data.id)
    assert delete_result.ok is True
    assert api.list_shift_pattern_days(created.data.id).data == ()
