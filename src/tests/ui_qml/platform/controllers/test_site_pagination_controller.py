"""`PlatformSiteController` pagination/search state machine: page resets to
1 whenever the page size or search text changes (so a stale page index
never silently returns an out-of-range/empty page), and an invalid page
size falls back to the standard default rather than being accepted. Mirrors
test_organization_pagination_controller.py's own coverage."""

from __future__ import annotations

from src.ui_qml.platform.controllers.sites.site_controller import PlatformSiteController
from src.ui_qml.platform.presenters.sites.site_catalog_presenter import (
    PlatformSiteCatalogPresenter,
)


def test_default_page_size_is_25_and_options_are_25_50_100():
    controller = PlatformSiteController(PlatformSiteCatalogPresenter())
    assert controller.sitePageSizeOptions == [25, 50, 100]
    controller.refresh()
    assert controller.sites["pageSize"] == 25
    assert controller.sites["page"] == 1


def test_changing_page_size_resets_to_page_one():
    controller = PlatformSiteController(PlatformSiteCatalogPresenter())
    controller.refresh()
    controller.setSitePage(3)
    assert controller.sites["page"] == 3

    controller.setSitePageSize(50)
    assert controller.sites["page"] == 1
    assert controller.sites["pageSize"] == 50


def test_changing_search_text_resets_to_page_one():
    controller = PlatformSiteController(PlatformSiteCatalogPresenter())
    controller.refresh()
    controller.setSitePage(2)

    controller.setSiteSearchText("acme")
    assert controller.sites["page"] == 1
    assert controller.siteSearchText == "acme"


def test_invalid_page_size_falls_back_to_default():
    controller = PlatformSiteController(PlatformSiteCatalogPresenter())
    controller.refresh()
    controller.setSitePageSize(17)
    assert controller.sites["pageSize"] == 25


def test_page_requested_below_one_is_clamped():
    controller = PlatformSiteController(PlatformSiteCatalogPresenter())
    controller.refresh()
    controller.setSitePage(-5)
    assert controller.sites["page"] == 1
