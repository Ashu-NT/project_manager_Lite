"""`PlatformOrganizationController` pagination/search state machine: page
resets to 1 whenever the page size or search text changes (so a stale page
index never silently returns an out-of-range/empty page), and an invalid
page size falls back to the standard default rather than being accepted."""

from __future__ import annotations

from src.ui_qml.platform.controllers.organizations.organization_controller import (
    PlatformOrganizationController,
)
from src.ui_qml.platform.presenters.organizations.organization_catalog_presenter import (
    PlatformOrganizationCatalogPresenter,
)


def test_default_page_size_is_25_and_options_are_25_50_100():
    controller = PlatformOrganizationController(PlatformOrganizationCatalogPresenter())
    assert controller.organizationPageSizeOptions == [25, 50, 100]
    controller.refresh()
    assert controller.organizations["pageSize"] == 25
    assert controller.organizations["page"] == 1


def test_changing_page_size_resets_to_page_one():
    controller = PlatformOrganizationController(PlatformOrganizationCatalogPresenter())
    controller.refresh()
    controller.setOrganizationPage(3)
    assert controller.organizations["page"] == 3

    controller.setOrganizationPageSize(50)
    assert controller.organizations["page"] == 1
    assert controller.organizations["pageSize"] == 50


def test_changing_search_text_resets_to_page_one():
    controller = PlatformOrganizationController(PlatformOrganizationCatalogPresenter())
    controller.refresh()
    controller.setOrganizationPage(2)

    controller.setOrganizationSearchText("acme")
    assert controller.organizations["page"] == 1
    assert controller.organizationSearchText == "acme"


def test_invalid_page_size_falls_back_to_default():
    controller = PlatformOrganizationController(PlatformOrganizationCatalogPresenter())
    controller.refresh()
    controller.setOrganizationPageSize(17)
    assert controller.organizations["pageSize"] == 25


def test_page_requested_below_one_is_clamped():
    controller = PlatformOrganizationController(PlatformOrganizationCatalogPresenter())
    controller.refresh()
    controller.setOrganizationPage(-5)
    assert controller.organizations["page"] == 1
