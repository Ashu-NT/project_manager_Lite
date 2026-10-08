from __future__ import annotations

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.platform.api.desktop.history.activity.activity import (
    PlatformActivityDesktopApi,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.platform.controllers.common.history_preview import run_history_preview
from src.ui_qml.platform.controllers.departments.department_controller import (
    PlatformDepartmentController,
)
from src.ui_qml.platform.controllers.employees.employee_controller import (
    PlatformEmployeeController,
)
from src.ui_qml.platform.controllers.organizations.organization_controller import (
    PlatformOrganizationController,
)
from src.ui_qml.platform.controllers.sites.site_controller import PlatformSiteController


def test_empty_history_is_not_an_error() -> None:
    messages: list[str] = []
    result = run_history_preview(
        operation=lambda: [],
        set_error_message=messages.append,
        label="test activity",
    )
    assert result == []
    assert messages == [""]


def test_history_permission_denial_is_visible_as_safe_error() -> None:
    messages: list[str] = []

    def denied() -> list[dict[str, object]]:
        raise BusinessRuleError("Permission denied for activity.", code="PERMISSION_DENIED")

    assert run_history_preview(
        operation=denied,
        set_error_message=messages.append,
        label="test activity",
    ) == []
    assert messages == ["Permission denied for activity."]


def test_history_query_failure_does_not_leak_internal_error() -> None:
    messages: list[str] = []

    def broken_query() -> list[dict[str, object]]:
        raise RuntimeError("SELECT secret_column FROM private_table")

    assert run_history_preview(
        operation=broken_query,
        set_error_message=messages.append,
        label="test activity",
    ) == []
    assert messages == ["History could not be loaded. Please try again."]


def test_desktop_activity_preview_does_not_turn_denial_into_empty_history() -> None:
    class DeniedActivityService:
        def list_recent_for_organization_id(self, *args, **kwargs):
            raise BusinessRuleError("Permission denied for activity.", code="PERMISSION_DENIED")

        def list_recent_for_entity(self, *args, **kwargs):
            raise BusinessRuleError("Permission denied for activity.", code="PERMISSION_DENIED")

    api = PlatformActivityDesktopApi(activity_service=DeniedActivityService())
    with pytest.raises(BusinessRuleError, match="Permission denied"):
        api.list_for_organization_overview("org-1")
    with pytest.raises(BusinessRuleError, match="Permission denied"):
        api.list_for_entity_overview("site", "site-1", "org-1")


def test_organization_detail_controller_sanitizes_preview_failure() -> None:
    class BrokenPresenter:
        def build_detail_context(self, organization_id):
            raise RuntimeError("SELECT secret_column FROM private_table")

        def build_recent_activity(self, organization_id):
            raise BusinessRuleError("Permission denied for activity.", code="PERMISSION_DENIED")

    controller = PlatformOrganizationController(presenter=BrokenPresenter())
    assert controller.organizationDetailContext("org-1") == {
        "statistics": {},
        "recentActivity": [],
    }
    assert controller.errorMessage == "The action could not be completed. Please try again."
    assert controller.organizationActivity("org-1") == []
    assert controller.errorMessage == "Permission denied for activity."


@pytest.mark.parametrize(
    ("controller_type", "slot_name"),
    (
        (PlatformSiteController, "siteActivity"),
        (PlatformDepartmentController, "departmentActivity"),
        (PlatformEmployeeController, "employeeActivity"),
    ),
)
def test_entity_detail_preview_controllers_show_safe_error(controller_type, slot_name) -> None:
    class DeniedPresenter:
        def build_recent_activity(self, entity_id, organization_id):
            raise BusinessRuleError("Permission denied for activity.", code="PERMISSION_DENIED")

    controller = controller_type(presenter=object(), activity_presenter=DeniedPresenter())
    assert getattr(controller, slot_name)("entity-1", "org-1") == []
    assert controller.errorMessage == "Permission denied for activity."


def test_admin_workspace_exposes_delegated_history_error_to_qml(services) -> None:
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.adminWorkspace

    class DeniedPresenter:
        def build_recent_activity(self, *args, **kwargs):
            raise BusinessRuleError("Permission denied for activity.", code="PERMISSION_DENIED")

    controller._site_controller._activity_presenter = DeniedPresenter()
    assert controller.siteActivity("site-1", "org-1") == []
    assert controller.errorMessage == "Permission denied for activity."

    controller._calendar_controller._activity_presenter = DeniedPresenter()
    assert controller.calendarActivity("calendar-1", "org-1") == []
    assert controller.errorMessage == "Permission denied for activity."
