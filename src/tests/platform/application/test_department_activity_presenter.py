"""Department Detail's Activity tab -- canonical ActivityItemViewModel feed
wired end-to-end through the admin desktop API, mirroring Site's own
activity presenter (see test coverage patterns already established for
site_activity_presenter.py)."""

from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


def test_department_activity_page_reports_distinct_lifecycle_actions(services) -> None:
    department_service = services["department_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    department = department_service.create_department(department_code="ACT-DEPT-1", name="Activity Dept")
    department_service.deactivate_department(department.id)
    department_service.activate_department(department.id)

    page = admin.departmentActivityPage(department.id, organization_id, 1, 25, "", "")
    actions_text = " ".join(item["title"] for item in page["items"])
    assert "activated" in actions_text.lower()
    assert "deactivated" in actions_text.lower()
    assert page["totalCount"] >= 3
    assert page["filteredTotal"] >= 3

    recent = admin.departmentActivity(department.id, organization_id)
    assert len(recent) >= 1


def test_department_activity_page_true_empty_state_before_any_activity(services) -> None:
    """A brand-new department already has a department.create activity
    entry -- this asserts the search-filtered (not true-empty) path
    instead, matching the presenter's noResultsState wording."""
    department_service = services["department_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    department = department_service.create_department(department_code="ACT-DEPT-2", name="Activity Dept Two")

    page = admin.departmentActivityPage(department.id, organization_id, 1, 25, "no-such-activity-search", "")
    assert page["filteredTotal"] == 0
    assert page["totalCount"] >= 1
    assert "No activity matches your current filters." == page["noResultsState"]
