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
)
from src.core.platform.application.time_management.calendar.enterprise_calendar_service import (
    EnterpriseCalendarService,
)
from src.core.platform.application.time_management.calendar.definitions.working_rule_service import WorkingRuleService
from src.core.platform.application.time_management.calendar.definitions.calendar_exception_service import (
    CalendarExceptionService,
)
from src.core.platform.application.time_management.calendar.assignment.calendar_assignment_service import (
    CalendarAssignmentService,
)
from src.core.platform.application.time_management.calendar.capacity.enterprise_calendar_resolver import (
    EnterpriseCalendarResolver,
)
from src.core.platform.application.time_management.calendar.capacity.working_time_calculator import WorkingTimeCalculator


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
def seeded_assignment_entities(db_session, org_id):
    from datetime import datetime, timezone

    from src.core.platform.infrastructure.persistence.orm.master_data.site.sites import SiteORM

    now = datetime.now(timezone.utc)
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
def assignment_service(db_session, repos, mock_user_session, seeded_assignment_entities):
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
# Tests — EnterpriseCalendarResolver
# ---------------------------------------------------------------------------


def test_resolver_returns_unavailable_with_no_global_calendar(resolver):
    ctx = resolver.resolve_calendar_context(target_date=date(2026, 6, 1))
    assert ctx.available_hours == 0.0  # no rules means no working hours
    assert ctx.source_chain == []


def test_resolver_source_chain_global(resolver, repos, global_cal, rule_service, org_id):
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
    from src.core.platform.application.time_management.calendar.enterprise_calendar_service import (
        _VALID_GRANULARITIES,
    )
    assert 5 in _VALID_GRANULARITIES
    assert 15 in _VALID_GRANULARITIES
    assert 7 not in _VALID_GRANULARITIES
