"""department_calendar_summary() resolves a Department's EFFECTIVE calendar
through the real chain: a direct Department override, else -- only when the
Department belongs to a Site -- that Site's own effective calendar, else the
Organization's default GLOBAL calendar directly. Mirrors the test coverage
pattern already established for site_calendar_summary() in
test_site_ui_modernization.py."""

from __future__ import annotations

from types import SimpleNamespace

from src.application.runtime import build_desktop_api_registry
from src.core.platform.api.desktop.time_management.calendar.models.enterprise_calendar import (
    DeptCalendarAssignCommand,
    SiteCalendarAssignCommand,
)
from src.ui_qml.platform.controllers.calendars.context import department_calendar_summary


def _fake_controller(registry) -> SimpleNamespace:
    return SimpleNamespace(
        _enterprise_calendar_api=registry.platform_enterprise_calendar,
        _runtime_api=registry.platform_runtime,
    )


def test_department_calendar_summary_inherited_from_organization_when_no_site_and_no_override(services) -> None:
    department_service = services["department_service"]
    department = department_service.create_department(department_code="DCAL-1", name="No Site Dept")
    organization_id = department.organization_id

    registry = build_desktop_api_registry(services)
    controller = _fake_controller(registry)

    summary = department_calendar_summary(controller, department.id, organization_id, "")

    assert summary["hasCalendar"] is True
    assert summary["source"] == "Inherited from Organization"
    assert summary["calendarName"]


def test_department_calendar_summary_inherited_from_site_when_site_has_override(services) -> None:
    department_service = services["department_service"]
    site_service = services["site_service"]
    site = site_service.create_site(site_code="DCAL-SITE-1", name="Dept Cal Site One")
    department = department_service.create_department(
        department_code="DCAL-2", name="Site Dept", site_id=site.id
    )
    organization_id = department.organization_id

    registry = build_desktop_api_registry(services)
    calendars_result = registry.platform_enterprise_calendar.list_calendars()
    assert calendars_result.ok and calendars_result.data
    calendar_id = calendars_result.data[0].id
    assign_result = registry.platform_enterprise_calendar.assign_site_calendar(
        SiteCalendarAssignCommand(site_id=site.id, calendar_id=calendar_id)
    )
    assert assign_result.ok, assign_result.error

    controller = _fake_controller(registry)
    summary = department_calendar_summary(controller, department.id, organization_id, site.id)

    assert summary["hasCalendar"] is True
    assert summary["source"] == "Inherited from Site"
    assert summary["calendarId"] == calendar_id


def test_department_calendar_summary_inherited_from_organization_when_site_has_no_override(services) -> None:
    department_service = services["department_service"]
    site_service = services["site_service"]
    site = site_service.create_site(site_code="DCAL-SITE-2", name="Dept Cal Site Two")
    department = department_service.create_department(
        department_code="DCAL-3", name="Site Dept Two", site_id=site.id
    )
    organization_id = department.organization_id

    registry = build_desktop_api_registry(services)
    controller = _fake_controller(registry)
    summary = department_calendar_summary(controller, department.id, organization_id, site.id)

    assert summary["hasCalendar"] is True
    assert summary["source"] == "Inherited from Organization"


def test_department_calendar_summary_is_department_override_when_department_has_its_own_assignment(services) -> None:
    department_service = services["department_service"]
    site_service = services["site_service"]
    site = site_service.create_site(site_code="DCAL-SITE-3", name="Dept Cal Site Three")
    department = department_service.create_department(
        department_code="DCAL-4", name="Override Dept", site_id=site.id
    )
    organization_id = department.organization_id

    registry = build_desktop_api_registry(services)
    calendars_result = registry.platform_enterprise_calendar.list_calendars()
    assert calendars_result.ok and calendars_result.data
    calendar_id = calendars_result.data[0].id

    # The Site also has its own override -- the Department's own override
    # must still win over it.
    site_assign = registry.platform_enterprise_calendar.assign_site_calendar(
        SiteCalendarAssignCommand(site_id=site.id, calendar_id=calendar_id)
    )
    assert site_assign.ok, site_assign.error
    department_assign = registry.platform_enterprise_calendar.assign_department_calendar(
        DeptCalendarAssignCommand(department_id=department.id, calendar_id=calendar_id)
    )
    assert department_assign.ok, department_assign.error

    controller = _fake_controller(registry)
    summary = department_calendar_summary(controller, department.id, organization_id, site.id)

    assert summary["hasCalendar"] is True
    assert summary["source"] == "Department override"
    assert summary["calendarId"] == calendar_id


def test_department_calendar_summary_empty_when_department_id_blank(services) -> None:
    registry = build_desktop_api_registry(services)
    controller = _fake_controller(registry)

    summary = department_calendar_summary(controller, "", "some-org-id", "")

    assert summary["hasCalendar"] is False
