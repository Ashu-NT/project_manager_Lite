"""End-to-end test that the PM Scheduling desktop API, when wired to a real
PlatformCalendarDesktopApi, reads/writes the real Platform Enterprise
Calendar instead of the legacy hard-coded stub."""

from __future__ import annotations

from datetime import date, time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.modules.project_management.api.desktop.scheduling.api import (
    ProjectManagementSchedulingDesktopApi,
)
from src.core.platform.api.desktop.time_management.calendar.platform_calendar import (
    PlatformCalendarDesktopApi,
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
from src.core.platform.application.time_management.calendar.definitions.commands.calendar_exception_commands import (
    CalendarExceptionCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.calendar_exception_queries import (
    CalendarExceptionQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.recurring_event_commands import (
    RecurringEventCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.recurring_event_queries import (
    RecurringEventQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.shift_pattern_commands import (
    ShiftPatternCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.shift_pattern_queries import (
    ShiftPatternQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.working_rule_commands import (
    WorkingRuleCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.working_rule_queries import (
    WorkingRuleQueryHandler,
)
from src.core.platform.application.time_management.calendar.commands.platform_calendar_commands import (
    PlatformCalendarCommandHandler,
)
from src.core.platform.application.time_management.calendar.queries.platform_calendar_queries import (
    PlatformCalendarQueryHandler,
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
    return "org-pm-cal-wiring"


@pytest.fixture
def tenant_context(org_id):
    from dataclasses import dataclass
    from unittest.mock import MagicMock

    @dataclass
    class FakeOrg:
        id: str = org_id

    @dataclass
    class FakeContext:
        tenant_id: str = "tenant-pm-cal-wiring"
        organization_id: str = org_id
        organization: FakeOrg | None = None

    context = MagicMock()
    context.require_active_organization_id.return_value = org_id
    context.get_active_organization_id.return_value = org_id
    context.get_active_organization.return_value = FakeOrg()
    context.get_active_tenant_id.return_value = "tenant-pm-cal-wiring"
    context.require_active_scope_ids.return_value = FakeContext(organization=FakeOrg())
    context.require_organization_context.return_value = FakeContext(
        organization=FakeOrg()
    )
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
    from dataclasses import dataclass
    from unittest.mock import MagicMock

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
def desktop_api(
    db_session, repos, mock_org_repo, mock_user_session, tenant_context, org_id
):
    from unittest.mock import MagicMock

    cal_commands = PlatformCalendarCommandHandler(
        session=db_session,
        calendar_repo=repos["calendar"],
        assignment_repo=repos["assignment"],
        organization_repo=mock_org_repo,
        user_session=mock_user_session,
        tenant_context_service=tenant_context,
    )
    cal_queries = PlatformCalendarQueryHandler(
        calendar_repo=repos["calendar"],
        user_session=mock_user_session,
        tenant_context_service=tenant_context,
    )
    rule_commands = WorkingRuleCommandHandler(
        session=db_session,
        calendar_repo=repos["calendar"],
        rule_repo=repos["rule"],
        user_session=mock_user_session,
    )
    rule_queries = WorkingRuleQueryHandler(
        calendar_repo=repos["calendar"],
        rule_repo=repos["rule"],
        user_session=mock_user_session,
    )
    exception_commands = CalendarExceptionCommandHandler(
        session=db_session,
        calendar_repo=repos["calendar"],
        exception_repo=repos["exception"],
        user_session=mock_user_session,
    )
    exception_queries = CalendarExceptionQueryHandler(
        calendar_repo=repos["calendar"],
        exception_repo=repos["exception"],
        user_session=mock_user_session,
    )
    recurring_commands = RecurringEventCommandHandler(
        session=db_session,
        calendar_repo=repos["calendar"],
        event_repo=repos["recurring"],
        user_session=mock_user_session,
    )
    recurring_queries = RecurringEventQueryHandler(
        calendar_repo=repos["calendar"],
        event_repo=repos["recurring"],
        user_session=mock_user_session,
    )
    shift_pattern_commands = ShiftPatternCommandHandler(
        session=db_session,
        pattern_repo=repos["shift"],
        user_session=mock_user_session,
        tenant_context_service=tenant_context,
    )
    shift_pattern_queries = ShiftPatternQueryHandler(
        pattern_repo=repos["shift"],
        user_session=mock_user_session,
        tenant_context_service=tenant_context,
    )
    assignment_commands = CalendarAssignmentCommandHandler(
        session=db_session,
        calendar_repo=repos["calendar"],
        assignment_repo=repos["assignment"],
        project_assignment_repo=MagicMock(),
        resource_assignment_repo=MagicMock(),
        user_session=mock_user_session,
    )
    assignment_queries = CalendarAssignmentQueryHandler(
        assignment_repo=repos["assignment"],
        project_assignment_repo=MagicMock(),
        resource_assignment_repo=MagicMock(),
    )
    resolver = PlatformCalendarResolver(
        organization_id=org_id,
        calendar_repo=repos["calendar"],
        rule_repo=repos["rule"],
        exception_repo=repos["exception"],
        recurring_repo=repos["recurring"],
        assignment_repo=repos["assignment"],
        project_assignment_repo=MagicMock(),
        resource_assignment_repo=MagicMock(),
        calculator=WorkingTimeCalculator(),
    )

    global_cal = cal_commands.ensure_global_calendar(org_id)
    rule_commands.seed_standard_week(
        global_cal.id, start_time=time(8, 0), end_time=time(17, 0), break_minutes=60
    )

    platform_calendar_api = PlatformCalendarDesktopApi(
        platform_calendar_commands=cal_commands,
        platform_calendar_queries=cal_queries,
        working_rule_commands=rule_commands,
        working_rule_queries=rule_queries,
        calendar_exception_commands=exception_commands,
        calendar_exception_queries=exception_queries,
        recurring_event_commands=recurring_commands,
        recurring_event_queries=recurring_queries,
        shift_pattern_commands=shift_pattern_commands,
        shift_pattern_queries=shift_pattern_queries,
        calendar_assignment_commands=assignment_commands,
        calendar_assignment_queries=assignment_queries,
        resolver=resolver,
    )

    return ProjectManagementSchedulingDesktopApi(
        platform_calendar_api=platform_calendar_api,
    ), global_cal


def test_list_calendars_reflects_real_platform_calendar(desktop_api):
    api, global_cal = desktop_api
    options = api.list_calendars()
    assert len(options) == 1
    assert options[0].value == global_cal.id
    assert options[0].label == global_cal.name


def test_get_calendar_snapshot_reflects_real_working_rules(desktop_api):
    api, global_cal = desktop_api
    snapshot = api.get_calendar_snapshot(global_cal.id)
    assert snapshot.calendar_id == global_cal.id
    assert snapshot.calendar_name == global_cal.name
    working_labels = [d.label for d in snapshot.working_days if d.checked]
    assert working_labels == ["Mon", "Tue", "Wed", "Thu", "Fri"]
    assert snapshot.hours_per_day == 8.0
    assert snapshot.holidays == ()


def test_get_calendar_snapshot_falls_back_to_default_when_no_id_given(desktop_api):
    api, global_cal = desktop_api
    snapshot = api.get_calendar_snapshot()
    assert snapshot.calendar_id == global_cal.id


def test_calculate_working_days_uses_real_calendar(desktop_api):
    from src.core.modules.project_management.application.scheduling.dto import (
        SchedulingWorkingDayCalculationCommand,
    )

    api, _ = desktop_api
    result = api.calculate_working_days(
        SchedulingWorkingDayCalculationCommand(
            start_date=date(2026, 6, 1), working_days=5
        )
    )
    # 2026-06-01 is a Monday; 5 working days lands on Friday 2026-06-05.
    assert result.result_date == date(2026, 6, 5)
    assert result.skipped_non_working_days == 0
