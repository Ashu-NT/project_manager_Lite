from __future__ import annotations

import pytest
from sqlalchemy import select

from src.core.platform.infrastructure.persistence.orm.time_management.calendar.enterprise_calendar import (
    CalendarWorkingRuleORM,
    PlatformCalendarORM,
)


def _global_calendar_row(session, organization_id: str):
    return session.execute(
        select(PlatformCalendarORM).where(
            PlatformCalendarORM.organization_id == organization_id,
            PlatformCalendarORM.calendar_type == "GLOBAL",
        )
    ).scalar_one_or_none()


def test_create_organization_transactionally_creates_exactly_one_default_calendar(services, session):
    """Every organization has exactly one default calendar, created in the
    SAME transaction as the organization itself -- not a best-effort
    follow-up call. Verified directly against the ORM rows (not through
    PlatformCalendarRepository, which is scoped to the caller's ACTIVE
    organization and can't see a just-created, not-yet-active one)."""
    organization_service = services["organization_service"]

    org = organization_service.create_organization(
        organization_code="CAL-DEFAULT", display_name="Calendar Default Org"
    )

    calendar = _global_calendar_row(session, org.id)
    assert calendar is not None
    assert calendar.code == "GLOBAL"
    assert calendar.is_default is True
    assert calendar.tenant_id == org.tenant_id

    rules = session.execute(
        select(CalendarWorkingRuleORM)
        .where(CalendarWorkingRuleORM.calendar_id == calendar.id)
        .order_by(CalendarWorkingRuleORM.weekday)
    ).scalars().all()
    assert len(rules) == 7
    working_days = {r.weekday for r in rules if r.is_working_day}
    assert working_days == {0, 1, 2, 3, 4}  # Mon-Fri
    monday = next(r for r in rules if r.weekday == 0)
    assert monday.start_time.strftime("%H:%M") == "08:00"
    assert monday.end_time.strftime("%H:%M") == "17:00"


def test_create_organization_rolls_back_entirely_if_default_calendar_seeding_fails(services, monkeypatch):
    """The organization cannot exist without its required calendar: if
    seeding the calendar rows fails, the organization row must not be
    committed either -- both happen in the one transaction."""
    organization_service = services["organization_service"]

    import src.core.platform.application.master_data.org.organization_service as org_service_module

    def _boom(session, organization):
        raise RuntimeError("simulated calendar seeding failure")

    monkeypatch.setattr(org_service_module, "_add_default_calendar_rows", _boom)

    with pytest.raises(RuntimeError, match="simulated calendar seeding failure"):
        organization_service.create_organization(
            organization_code="CAL-ROLLBACK", display_name="Calendar Rollback Org"
        )

    codes = {row.organization_code for row in organization_service.list_organizations()}
    assert "CAL-ROLLBACK" not in codes


def test_organization_service_bootstraps_default_and_activates_another_organization_independently(services):
    """Activating one organization must never deactivate a sibling -- multiple organizations in
    the same tenant may be `status == ACTIVE` simultaneously."""
    organization_service = services["organization_service"]

    initial_rows = organization_service.list_organizations()
    assert len(initial_rows) == 1
    assert initial_rows[0].organization_code == "DEFAULT"
    assert initial_rows[0].status == "active"

    second = organization_service.create_organization(
        organization_code="NORTH",
        display_name="North Division",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
    )
    organization_service.deactivate_organization(second.id)

    rows = organization_service.list_organizations()
    assert len(rows) == 2
    status_by_code = {row.organization_code: row.status for row in rows}
    assert status_by_code == {"DEFAULT": "active", "NORTH": "inactive"}

    organization_service.activate_organization(second.id)

    status_by_code = {
        row.organization_code: row.status
        for row in organization_service.list_organizations()
    }
    # Both organizations are active -- no mutual exclusion.
    assert status_by_code == {"DEFAULT": "active", "NORTH": "active"}


def test_organization_provisioning_seeds_requested_modules_and_switches_to_the_new_org(services):
    """New organizations are always created ACTIVE, and provisioning always switches the caller's
    session into the just-created organization."""
    app_service = services["platform_runtime_application_service"]
    tenant_context_service = services["tenant_context_service"]
    module_catalog = services["module_catalog_service"]

    default_organization = tenant_context_service.get_active_organization()
    assert default_organization.organization_code == "DEFAULT"
    assert module_catalog.is_enabled("project_management") is True

    created = app_service.provision_organization(
        organization_code="EMPTY",
        display_name="Empty Module Org",
        timezone_name="UTC",
        base_currency="EUR",
        initial_module_codes=[],
    )

    assert created.organization_code == "EMPTY"
    assert tenant_context_service.get_active_organization().organization_code == "EMPTY"
    assert module_catalog.current_context_label() == "Empty Module Org"
    assert module_catalog.is_enabled("project_management") is False
