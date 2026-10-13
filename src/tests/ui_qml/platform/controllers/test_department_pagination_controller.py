"""`PlatformDepartmentController` pagination/search/filter state machine:
page resets to 1 whenever the page size, search text, status filter, or
site filter changes (so a stale page index never silently returns an
out-of-range/empty page), and an invalid page size falls back to the
standard default rather than being accepted. Mirrors
test_site_pagination_controller.py's own coverage, plus the Site filter
dimension Department has and Site itself does not (Department is
Site-optional)."""

from __future__ import annotations

from src.ui_qml.platform.controllers.departments.department_controller import (
    PlatformDepartmentController,
)
from src.ui_qml.platform.presenters.departments.department_catalog_presenter import (
    PlatformDepartmentCatalogPresenter,
)


def test_default_page_size_is_25_and_options_are_25_50_100():
    controller = PlatformDepartmentController(PlatformDepartmentCatalogPresenter())
    assert controller.departmentPageSizeOptions == [25, 50, 100]
    controller.refresh()
    assert controller.departments["pageSize"] == 25
    assert controller.departments["page"] == 1


def test_changing_page_size_resets_to_page_one():
    controller = PlatformDepartmentController(PlatformDepartmentCatalogPresenter())
    controller.refresh()
    controller.setDepartmentPage(3)
    assert controller.departments["page"] == 3

    controller.setDepartmentPageSize(50)
    assert controller.departments["page"] == 1
    assert controller.departments["pageSize"] == 50


def test_changing_search_text_resets_to_page_one():
    controller = PlatformDepartmentController(PlatformDepartmentCatalogPresenter())
    controller.refresh()
    controller.setDepartmentPage(2)

    controller.setDepartmentSearchText("acme")
    assert controller.departments["page"] == 1
    assert controller.departmentSearchText == "acme"


def test_changing_status_filter_resets_to_page_one():
    controller = PlatformDepartmentController(PlatformDepartmentCatalogPresenter())
    controller.refresh()
    controller.setDepartmentPage(2)

    controller.setDepartmentStatusFilter("active")
    assert controller.departments["page"] == 1
    assert controller.departmentStatusFilter == "active"


def test_changing_site_filter_resets_to_page_one():
    controller = PlatformDepartmentController(PlatformDepartmentCatalogPresenter())
    controller.refresh()
    controller.setDepartmentPage(2)

    controller.setDepartmentSiteFilter("site-123")
    assert controller.departments["page"] == 1
    assert controller.departmentSiteFilter == "site-123"


def test_invalid_page_size_falls_back_to_default():
    controller = PlatformDepartmentController(PlatformDepartmentCatalogPresenter())
    controller.refresh()
    controller.setDepartmentPageSize(17)
    assert controller.departments["pageSize"] == 25


def test_page_requested_below_one_is_clamped():
    controller = PlatformDepartmentController(PlatformDepartmentCatalogPresenter())
    controller.refresh()
    controller.setDepartmentPage(-5)
    assert controller.departments["page"] == 1
