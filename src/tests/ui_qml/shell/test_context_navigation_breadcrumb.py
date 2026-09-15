from __future__ import annotations

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.modules.project_management.context_navigation import (
    build_pm_context_navigation,
)
from src.ui_qml.modules.project_management.controllers.common.pm_workspace_navigation_controller import (
    PMWorkspaceNavigationController,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog
from src.ui_qml.platform.navigation.platform_context_navigation import (
    build_platform_context_navigation,
)
from src.ui_qml.shell.context_navigation import resolve_breadcrumb


def test_grouped_destination_yields_three_segments():
    tree = build_platform_context_navigation(held_permissions=frozenset({"settings.manage"}))
    breadcrumb = resolve_breadcrumb(workspace_title="Platform", tree=tree, current_id="organizations")
    assert breadcrumb == ["Platform", "Organization", "Organizations"]


def test_ungrouped_root_destination_yields_two_segments():
    tree = build_platform_context_navigation(held_permissions=frozenset())
    breadcrumb = resolve_breadcrumb(workspace_title="Platform", tree=tree, current_id="overview")
    assert breadcrumb == ["Platform", "Overview"]


def test_unknown_destination_falls_back_to_workspace_only():
    tree = build_platform_context_navigation(held_permissions=frozenset())
    breadcrumb = resolve_breadcrumb(workspace_title="Platform", tree=tree, current_id="does-not-exist")
    assert breadcrumb == ["Platform"]


def test_pm_grouped_destination_matches_target_examples():
    tree = build_pm_context_navigation()

    assert resolve_breadcrumb(
        workspace_title="Project Management", tree=tree, current_id="projects"
    ) == ["Project Management", "Work", "Projects"]

    assert resolve_breadcrumb(
        workspace_title="Project Management", tree=tree, current_id="review_queue"
    ) == ["Project Management", "Workload Management", "Review Queue"]

    assert resolve_breadcrumb(
        workspace_title="Project Management", tree=tree, current_id="collaboration"
    ) == ["Project Management", "Governance", "Collaboration"]


def test_platform_access_breadcrumb_matches_target_example():
    tree = build_platform_context_navigation(held_permissions=frozenset({"access.manage"}))
    breadcrumb = resolve_breadcrumb(workspace_title="Platform", tree=tree, current_id="users")
    assert breadcrumb[0] == "Platform"
    assert breadcrumb[1] == "Identity & Access"


def test_platform_catalog_breadcrumb_updates_on_selection(services):
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)

    assert catalog.breadcrumb == ["Platform", "Overview"]

    catalog.selectDestination("settings")
    assert catalog.breadcrumb == ["Platform", "Administration", "Settings"]

    catalog.selectDestination("control_audit")
    assert catalog.breadcrumb == ["Platform", "Control", "Audit"]


def test_pm_controller_breadcrumb_updates_on_selection():
    controller = PMWorkspaceNavigationController()

    assert controller.breadcrumb == ["Project Management", "Overview"]

    controller.selectWorkspace("review_queue")
    assert controller.breadcrumb == ["Project Management", "Workload Management", "Review Queue"]
