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
from src.core.platform.domain.time_management.calendar.enterprise_calendar import CalendarType
from src.core.platform.application.time_management.calendar.enterprise_calendar_service import (
    EnterpriseCalendarService,
)
from src.core.platform.application.time_management.calendar.definitions.working_rule_service import WorkingRuleService
from src.core.platform.application.time_management.calendar.assignment.calendar_assignment_service import (
    CalendarAssignmentService,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError


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
            for site_id in ("site-x",)
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


def test_delete_calendar_blocked_if_assigned(cal_service, assignment_service, global_cal):
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


def test_working_rule_save_normalizes_dto_inputs(rule_service, global_cal):
    rule = rule_service.save_rule(
        f"  {global_cal.id}  ",
        weekday="1",
        is_working_day=True,
        start_time=time(8, 0),
        end_time=time(17, 0),
        break_minutes="45",
        hours_override="7.25",
        shift_code="  day  ",
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        priority="2",
    )

    assert rule.calendar_id == global_cal.id
    assert rule.weekday == 1
    assert rule.break_minutes == 45
    assert rule.hours_override == 7.25
    assert rule.shift_code == "day"
    assert rule.priority == 2

    stored = next(item for item in rule_service.list_rules(global_cal.id) if item.id == rule.id)
    assert stored.calendar_id == global_cal.id
    assert stored.weekday == 1
