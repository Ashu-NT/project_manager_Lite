"""Backend support added for the Site workspace UI/UX modernization pass:

1. Site's full physical address (address_line_1/2, postal_code, region) --
   already real domain/API fields, just not previously surfaced through the
   presenter's create_site/update_site/_serialize_site -- for the Overview
   "Physical Address" card and the Site Editor dialog.
2. site_calendar_summary() -- resolves a Site's EFFECTIVE calendar (its own
   direct override, else the Organization's default GLOBAL calendar) into
   one display-ready summary, fixing the previous generic "inherits the
   Global calendar by default" wording that never named the actual
   fallback calendar.
"""

from __future__ import annotations

from types import SimpleNamespace

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.platform.controllers.calendars.context import site_calendar_summary
from src.ui_qml.platform.presenters.sites.site_catalog_presenter import (
    PlatformSiteCatalogPresenter,
)


def test_create_and_update_site_round_trip_full_address(services) -> None:
    registry = build_desktop_api_registry(services)
    presenter = PlatformSiteCatalogPresenter(site_api=registry.platform_site)

    create_result = presenter.create_site({
        "siteCode": "ADDR-1",
        "name": "Addressed Site",
        "city": "Douala",
        "region": "Littoral",
        "addressLine1": "12 Rue de la Paix",
        "addressLine2": "Building B",
        "postalCode": "00237",
        "country": "Cameroon",
    })
    assert create_result.ok, create_result.error
    site_id = create_result.data.id

    catalog = presenter.build_catalog()
    row = next(item for item in catalog.items if item.id == site_id)
    assert row.state["addressLine1"] == "12 Rue de la Paix"
    assert row.state["addressLine2"] == "Building B"
    assert row.state["postalCode"] == "00237"
    assert row.state["region"] == "Littoral"

    update_result = presenter.update_site({
        "siteId": site_id,
        "expectedVersion": create_result.data.version,
        "siteCode": "ADDR-1",
        "name": "Addressed Site",
        "city": "Douala",
        "region": "Centre",
        "addressLine1": "34 Rue de la Paix",
        "addressLine2": "",
        "postalCode": "00238",
        "country": "Cameroon",
    })
    assert update_result.ok, update_result.error
    assert update_result.data.region == "Centre"
    assert update_result.data.address_line_1 == "34 Rue de la Paix"
    assert update_result.data.postal_code == "00238"


def _fake_controller(registry) -> SimpleNamespace:
    return SimpleNamespace(
        _enterprise_calendar_api=registry.platform_enterprise_calendar,
        _runtime_api=registry.platform_runtime,
    )


def test_site_calendar_summary_is_inherited_from_organization_when_no_override(services) -> None:
    site_service = services["site_service"]
    site = site_service.create_site(site_code="CAL-1", name="Calendar Site One")
    organization_id = site.organization_id

    registry = build_desktop_api_registry(services)
    controller = _fake_controller(registry)

    summary = site_calendar_summary(controller, site.id, organization_id)

    assert summary["hasCalendar"] is True
    assert summary["source"] == "inherited"
    assert summary["calendarName"]


def test_site_calendar_summary_is_override_when_site_has_its_own_assignment(services) -> None:
    site_service = services["site_service"]
    site = site_service.create_site(site_code="CAL-2", name="Calendar Site Two")
    organization_id = site.organization_id

    registry = build_desktop_api_registry(services)
    calendars_result = registry.platform_enterprise_calendar.list_calendars()
    assert calendars_result.ok and calendars_result.data, "expected at least the seeded default calendar"
    calendar_id = calendars_result.data[0].id

    assign_result = registry.platform_enterprise_calendar.assign_site_calendar(
        __import__(
            "src.core.platform.api.desktop.time_management.calendar.models.enterprise_calendar",
            fromlist=["SiteCalendarAssignCommand"],
        ).SiteCalendarAssignCommand(site_id=site.id, calendar_id=calendar_id)
    )
    assert assign_result.ok, assign_result.error

    controller = _fake_controller(registry)
    summary = site_calendar_summary(controller, site.id, organization_id)

    assert summary["hasCalendar"] is True
    assert summary["source"] == "override"
    assert summary["calendarId"] == calendar_id


def test_site_calendar_summary_empty_when_site_id_blank(services) -> None:
    registry = build_desktop_api_registry(services)
    controller = _fake_controller(registry)

    summary = site_calendar_summary(controller, "", "some-org-id")

    assert summary["hasCalendar"] is False
