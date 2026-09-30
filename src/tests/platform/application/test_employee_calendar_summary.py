"""employee_calendar_summary() resolves an Employee's EFFECTIVE calendar
through the real chain: a direct Employee override, else the Employee's
Department effective calendar (itself already Department-override-or-Site-
or-Organization), else -- when there is no Department -- the Employee's own
Site effective calendar, else the Organization's default GLOBAL calendar
directly. Mirrors the test coverage pattern already established for
department_calendar_summary() in test_department_calendar_summary.py."""

from __future__ import annotations

from types import SimpleNamespace

from src.application.runtime import build_desktop_api_registry
from src.core.platform.api.desktop.time_management.calendar.models.enterprise_calendar import (
    DeptCalendarAssignCommand,
    EmpCalendarAssignCommand,
    SiteCalendarAssignCommand,
)
from src.ui_qml.platform.controllers.calendars.context import employee_calendar_summary


def _fake_controller(registry) -> SimpleNamespace:
    return SimpleNamespace(
        _enterprise_calendar_api=registry.platform_enterprise_calendar,
        _runtime_api=registry.platform_runtime,
    )


def test_employee_calendar_summary_inherited_from_organization_when_no_department_or_site(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    department = department_service.create_department(department_code="ECAL-D1", name="No Site Dept")
    employee = employee_service.create_employee(
        employee_code="ECAL-E1", full_name="Employee One", department_id=department.id
    )
    organization_id = employee.organization_id

    registry = build_desktop_api_registry(services)
    controller = _fake_controller(registry)

    summary = employee_calendar_summary(controller, employee.id, organization_id, department.id, "")

    assert summary["hasCalendar"] is True
    assert summary["source"] == "Inherited from Organization"
    assert summary["calendarName"]


def test_employee_calendar_summary_inherited_from_department_when_department_has_override(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    department = department_service.create_department(department_code="ECAL-D2", name="Override Dept")
    employee = employee_service.create_employee(
        employee_code="ECAL-E2", full_name="Employee Two", department_id=department.id
    )
    organization_id = employee.organization_id

    registry = build_desktop_api_registry(services)
    calendars_result = registry.platform_enterprise_calendar.list_calendars()
    assert calendars_result.ok and calendars_result.data
    calendar_id = calendars_result.data[0].id
    assign_result = registry.platform_enterprise_calendar.assign_department_calendar(
        DeptCalendarAssignCommand(department_id=department.id, calendar_id=calendar_id)
    )
    assert assign_result.ok, assign_result.error

    controller = _fake_controller(registry)
    summary = employee_calendar_summary(controller, employee.id, organization_id, department.id, "")

    assert summary["hasCalendar"] is True
    assert summary["source"] == "Inherited from Department"
    assert summary["calendarId"] == calendar_id


def test_employee_calendar_summary_inherited_from_site_when_department_has_no_override(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    site_service = services["site_service"]
    site = site_service.create_site(site_code="ECAL-SITE-1", name="Employee Cal Site One")
    department = department_service.create_department(
        department_code="ECAL-D3", name="Site Dept", site_id=site.id
    )
    employee = employee_service.create_employee(
        employee_code="ECAL-E3", full_name="Employee Three", department_id=department.id, site_id=site.id
    )
    organization_id = employee.organization_id

    registry = build_desktop_api_registry(services)
    calendars_result = registry.platform_enterprise_calendar.list_calendars()
    assert calendars_result.ok and calendars_result.data
    calendar_id = calendars_result.data[0].id
    assign_result = registry.platform_enterprise_calendar.assign_site_calendar(
        SiteCalendarAssignCommand(site_id=site.id, calendar_id=calendar_id)
    )
    assert assign_result.ok, assign_result.error

    controller = _fake_controller(registry)
    summary = employee_calendar_summary(controller, employee.id, organization_id, department.id, site.id)

    assert summary["hasCalendar"] is True
    assert summary["source"] == "Inherited from Site"
    assert summary["calendarId"] == calendar_id


def test_employee_calendar_summary_is_employee_override_when_employee_has_its_own_assignment(services) -> None:
    employee_service = services["employee_service"]
    department_service = services["department_service"]
    site_service = services["site_service"]
    site = site_service.create_site(site_code="ECAL-SITE-2", name="Employee Cal Site Two")
    department = department_service.create_department(
        department_code="ECAL-D4", name="Employee Override Dept", site_id=site.id
    )
    employee = employee_service.create_employee(
        employee_code="ECAL-E4", full_name="Employee Four", department_id=department.id, site_id=site.id
    )
    organization_id = employee.organization_id

    registry = build_desktop_api_registry(services)
    calendars_result = registry.platform_enterprise_calendar.list_calendars()
    assert calendars_result.ok and calendars_result.data
    calendar_id = calendars_result.data[0].id

    # The Department also has its own override -- the Employee's own
    # override must still win over it.
    department_assign = registry.platform_enterprise_calendar.assign_department_calendar(
        DeptCalendarAssignCommand(department_id=department.id, calendar_id=calendar_id)
    )
    assert department_assign.ok, department_assign.error
    employee_assign = registry.platform_enterprise_calendar.assign_employee_calendar(
        EmpCalendarAssignCommand(employee_id=employee.id, calendar_id=calendar_id)
    )
    assert employee_assign.ok, employee_assign.error

    controller = _fake_controller(registry)
    summary = employee_calendar_summary(controller, employee.id, organization_id, department.id, site.id)

    assert summary["hasCalendar"] is True
    assert summary["source"] == "Employee override"
    assert summary["calendarId"] == calendar_id


def test_employee_calendar_summary_empty_when_employee_id_blank(services) -> None:
    registry = build_desktop_api_registry(services)
    controller = _fake_controller(registry)

    summary = employee_calendar_summary(controller, "", "some-org-id", "", "")

    assert summary["hasCalendar"] is False
