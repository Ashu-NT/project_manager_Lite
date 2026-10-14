"""PlatformDepartmentCatalogPresenter.build_catalog_page() -- the standalone
Departments workspace's server-side pagination, ambient-active-organization-
scoped (unlike build_catalog_page_for_organization's explicit organization_id
variant, used by Organization Detail's Departments tab). Covers search,
status filter, and the Site filter dimension Department has that Site's own
main workspace does not (Department is Site-optional)."""

from __future__ import annotations

from src.core.platform.contract.use_cases.master_data.department.commands import (
    DepartmentCreateCommand,
)
from src.core.platform.contract.use_cases.master_data.site.commands import (
    SiteCreateCommand,
)
from src.ui_qml.platform.presenters.departments.department_catalog_presenter import (
    PlatformDepartmentCatalogPresenter,
)


def _presenter(services) -> PlatformDepartmentCatalogPresenter:
    from src.core.platform.api.desktop.master_data.department.department import (
        PlatformDepartmentDesktopApi,
    )
    from src.core.platform.api.desktop.master_data.employee.employee import (
        PlatformEmployeeDesktopApi,
    )
    from src.core.platform.api.desktop.master_data.site.site import (
        PlatformSiteDesktopApi,
    )

    return PlatformDepartmentCatalogPresenter(
        department_api=PlatformDepartmentDesktopApi(
        department_commands=services["department_commands"],
        department_query=services["department_query"],
    ),
        site_api=PlatformSiteDesktopApi(
        site_commands=services["site_commands"],
        site_query=services["site_query"],
    ),
        employee_api=PlatformEmployeeDesktopApi(
            employee_commands=services["employee_commands"],
            employee_query=services["employee_query"],
            employee_documents=services["employee_document_commands"],
        ),
    )


def test_build_catalog_page_returns_paginated_result_for_active_organization(services) -> None:
    services["department_commands"].create_department(DepartmentCreateCommand(department_code="MW-D1", name="Engineering"))
    services["department_commands"].create_department(DepartmentCreateCommand(department_code="MW-D2", name="Sales"))

    presenter = _presenter(services)
    result = presenter.build_catalog_page(page=1, page_size=25)

    assert result.paginated is True
    assert result.page == 1
    assert result.page_size == 25
    assert result.total_count >= 2
    names = {item.title for item in result.items}
    assert {"Engineering", "Sales"}.issubset(names)
    # Inspector's "Organization" row (Identity group) resolves a real
    # display name here, unlike build_catalog_page_for_organization (used
    # by Organization Detail's own Departments tab, where showing the
    # organization you're already viewing would be redundant).
    engineering = next(item for item in result.items if item.title == "Engineering")
    assert engineering.state["organizationName"]


def test_build_catalog_page_search_filters_by_name(services) -> None:
    services["department_commands"].create_department(DepartmentCreateCommand(department_code="MW-SRCH-1", name="Payroll Operations"))
    services["department_commands"].create_department(DepartmentCreateCommand(department_code="MW-SRCH-2", name="Logistics"))

    presenter = _presenter(services)
    result = presenter.build_catalog_page(search="Payroll")

    names = [item.title for item in result.items]
    assert names == ["Payroll Operations"]
    assert result.filtered_total == 1


def test_build_catalog_page_status_filter_active_and_inactive(services) -> None:
    active_dept = services["department_commands"].create_department(DepartmentCreateCommand(department_code="MW-ST-1", name="Still Active"))
    inactive_dept = services["department_commands"].create_department(DepartmentCreateCommand(department_code="MW-ST-2", name="Now Inactive"))
    services["department_commands"].deactivate_department(inactive_dept.id)

    presenter = _presenter(services)

    active_result = presenter.build_catalog_page(status="active")
    active_names = {item.title for item in active_result.items}
    assert "Still Active" in active_names
    assert "Now Inactive" not in active_names

    inactive_result = presenter.build_catalog_page(status="inactive")
    inactive_names = {item.title for item in inactive_result.items}
    assert "Now Inactive" in inactive_names
    assert "Still Active" not in inactive_names

    assert active_dept.is_active is True


def test_build_catalog_page_site_filter_scopes_to_one_site(services) -> None:
    site_a = services["site_commands"].create_site(SiteCreateCommand(site_code="MW-SITE-A", name="Site A"))
    site_b = services["site_commands"].create_site(SiteCreateCommand(site_code="MW-SITE-B", name="Site B"))
    services["department_commands"].create_department(DepartmentCreateCommand(department_code="MW-SITE-D1", name="Dept On Site A", site_id=site_a.id))
    services["department_commands"].create_department(DepartmentCreateCommand(department_code="MW-SITE-D2", name="Dept On Site B", site_id=site_b.id))

    presenter = _presenter(services)
    result = presenter.build_catalog_page(site_id=site_a.id)

    names = {item.title for item in result.items}
    assert names == {"Dept On Site A"}


def test_build_catalog_page_true_empty_state_when_no_departments(services) -> None:
    presenter = _presenter(services)
    result = presenter.build_catalog_page()

    assert result.items == ()
    assert result.empty_state
    assert result.no_results_state


def test_build_catalog_page_filtered_empty_when_search_matches_nothing(services) -> None:
    services["department_commands"].create_department(DepartmentCreateCommand(department_code="MW-FE-1", name="Real Department"))

    presenter = _presenter(services)
    result = presenter.build_catalog_page(search="no-such-department-xyz")

    assert result.items == ()
    assert result.no_results_state
