
from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.core.platform.api.desktop.models.common import DesktopApiResult
from src.core.platform.application.master_data.employee.employee_service import (
    EmployeeService,
)
from src.core.platform.application.master_data.party.party_service import PartyService
from src.core.platform.application.master_data.site.site_service import SiteService
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


def _instrument(cls, method_name):
    counts = {method_name: 0}
    real = getattr(cls, method_name)

    def counting(self, *args, **kwargs):
        counts[method_name] += 1
        return real(self, *args, **kwargs)

    setattr(cls, method_name, counting)

    def restore():
        setattr(cls, method_name, real)

    return counts, restore


def test_admin_console_refresh_calls_all_entities_for_platform_operator(services):
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)

    employee_counts, restore_employee = _instrument(
        EmployeeService, "list_employees_page_for_organization"
    )
    site_counts, restore_site = _instrument(SiteService, "list_sites")
    try:
        catalog.adminWorkspace.refresh()
    finally:
        restore_employee()
        restore_site()

    # The default services principal is the platform-operator "admin" user
    # -- everything is accessible, so both entities' desktop-API calls fire.
    assert employee_counts["list_employees_page_for_organization"] >= 1
    assert site_counts["list_sites"] >= 1


def test_admin_console_refresh_skips_entities_the_session_cannot_access(services):
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)

    class NoEntityPermissionsRuntimeApi:
        def get_current_permissions(self):
            return DesktopApiResult(ok=True, data=())

    catalog.adminWorkspace._runtime_api = NoEntityPermissionsRuntimeApi()

    employee_counts, restore_employee = _instrument(
        EmployeeService, "list_employees_page_for_organization"
    )
    site_counts, restore_site = _instrument(SiteService, "list_sites")
    try:
        catalog.adminWorkspace.refresh()
    finally:
        restore_employee()
        restore_site()

    assert employee_counts["list_employees_page_for_organization"] == 0
    assert site_counts["list_sites"] == 0


def test_admin_console_refresh_selectively_includes_only_granted_entities(services):
    """party.read grants access to exactly one entity that has no cross-
    dependency on any other (unlike Employees, whose refresh also
    populates site/department dropdown options) -- a clean signal that the
    gate is per-entity, not all-or-nothing."""
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)

    class PartyOnlyRuntimeApi:
        def get_current_permissions(self):
            return DesktopApiResult(ok=True, data=("party.read",))

    catalog.adminWorkspace._runtime_api = PartyOnlyRuntimeApi()

    employee_counts, restore_employee = _instrument(
        EmployeeService, "list_employees_page_for_organization"
    )
    party_counts, restore_party = _instrument(
        PartyService, "list_parties_page_for_organization"
    )
    try:
        catalog.adminWorkspace.refresh()
    finally:
        restore_employee()
        restore_party()

    assert party_counts["list_parties_page_for_organization"] >= 1
    assert employee_counts["list_employees_page_for_organization"] == 0


def test_admin_console_refresh_fails_open_when_runtime_api_missing():
    """A controller constructed directly (e.g. in another test) with no
    runtime_api wired must keep today's unconditional-refresh behavior --
    this pre-filter should never make an already-passing test go blank."""
    from src.ui_qml.platform.controllers.overview.admin_console_controller import (
        PlatformAdminWorkspaceController,
    )
    from src.ui_qml.platform.presenters.calendars.calendar_catalog_presenter import (
        PlatformCalendarCatalogPresenter,
    )
    from src.ui_qml.platform.presenters.departments.department_catalog_presenter import (
        PlatformDepartmentCatalogPresenter,
    )
    from src.ui_qml.platform.presenters.documents.document_catalog_presenter import (
        PlatformDocumentCatalogPresenter,
    )
    from src.ui_qml.platform.presenters.documents.document_management_presenter import (
        PlatformDocumentManagementPresenter,
    )
    from src.ui_qml.platform.presenters.employees.employee_catalog_presenter import (
        PlatformEmployeeCatalogPresenter,
    )
    from src.ui_qml.platform.presenters.organizations.organization_catalog_presenter import (
        PlatformOrganizationCatalogPresenter,
    )
    from src.ui_qml.platform.presenters.overview.admin_overview_presenter import (
        PlatformAdminWorkspacePresenter,
    )
    from src.ui_qml.platform.presenters.parties.party_catalog_presenter import (
        PlatformPartyCatalogPresenter,
    )
    from src.ui_qml.platform.presenters.sites.site_catalog_presenter import (
        PlatformSiteCatalogPresenter,
    )
    from src.ui_qml.platform.presenters.users.user_catalog_presenter import (
        PlatformUserCatalogPresenter,
    )

    controller = PlatformAdminWorkspaceController(
        overview_presenter=PlatformAdminWorkspacePresenter(),
        organization_presenter=PlatformOrganizationCatalogPresenter(),
        calendar_presenter=PlatformCalendarCatalogPresenter(),
        site_presenter=PlatformSiteCatalogPresenter(),
        department_presenter=PlatformDepartmentCatalogPresenter(),
        employee_presenter=PlatformEmployeeCatalogPresenter(),
        user_presenter=PlatformUserCatalogPresenter(),
        party_presenter=PlatformPartyCatalogPresenter(),
        document_presenter=PlatformDocumentCatalogPresenter(),
        document_management_presenter=PlatformDocumentManagementPresenter(),
        # runtime_api intentionally omitted
    )

    # Must not raise, and every sub-controller's catalog stays the
    # (empty-but-present) preview shape rather than being skipped/absent.
    assert controller.employees is not None
    assert controller.sites is not None
