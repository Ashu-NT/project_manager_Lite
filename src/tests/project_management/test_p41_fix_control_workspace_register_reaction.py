from __future__ import annotations

import ast
import inspect

import pytest

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


def _wire_catalogs(services) -> tuple[PlatformWorkspaceCatalog, ProjectManagementWorkspaceCatalog]:
    registry = build_desktop_api_registry(services)
    platform_catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    pm_catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    pm_catalog.registerWorkspaceStale.connect(
        platform_catalog.controlWorkspace.onExternalViewStale
    )
    return platform_catalog, pm_catalog


def _setup(services):
    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        "P41-FIX Register project", financial_currency_code=organization.base_currency
    )
    return organization, project


# ---------------------------------------------------------------------------
# 1. Control's Register dependency is genuine -- proved from source, not asserted
# ---------------------------------------------------------------------------


def test_control_audit_feed_reads_a_module_agnostic_query_including_register_entries():
    import src.ui_qml.platform.presenters.control.control_presenter as presenter_module
    import src.ui_qml.platform.presenters.control.control_queue_presenter as queue_module

    overview_source = inspect.getsource(presenter_module.PlatformControlWorkspacePresenter.build_overview)
    feed_source = inspect.getsource(queue_module.PlatformControlQueuePresenter.build_audit_feed)
    assert "list_recent" in overview_source
    assert "list_recent" in feed_source
    assert "module=" not in feed_source, "the audit feed query is module-agnostic, not Register-specific"


# ---------------------------------------------------------------------------
# 2. Layering: Platform stays ignorant of Register/PM
# ---------------------------------------------------------------------------


def test_control_workspace_controller_imports_no_pm_module():
    import src.ui_qml.platform.controllers.control.control_workspace_controller as control_module

    tree = ast.parse(inspect.getsource(control_module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    for forbidden in ("project_management", "RegisterEntryChanged", "RegisterViewInvalidationAdapter"):
        assert not any(forbidden in name for name in names), names


def test_control_workspace_subscribes_to_zero_raw_register_domain_events():
    import src.ui_qml.platform.controllers.control.control_workspace_controller as control_module

    source = inspect.getsource(control_module)
    assert "RegisterEntryChanged" not in source
    assert "register_changed" not in source


# ---------------------------------------------------------------------------
# 3. End-to-end: Register mutation -> ViewInvalidation -> Control refresh, zero legacy Signal
# ---------------------------------------------------------------------------


def test_register_create_causes_control_refresh_via_view_invalidation_only(services):
    platform_catalog, _pm_catalog = _wire_catalogs(services)
    _, project = _setup(services)
    controller = platform_catalog.controlWorkspace
    controller.ensureLoaded()
    refresh_calls: list[str] = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    from src.core.modules.project_management.domain.risk.register import RegisterEntryType

    services["register_service"].create_entry(
        project.id, entry_type=RegisterEntryType.RISK, title="P41-FIX risk"
    )

    assert refresh_calls == ["refresh"]


def test_register_update_and_delete_also_cause_control_refresh(services):
    platform_catalog, _pm_catalog = _wire_catalogs(services)
    _, project = _setup(services)

    from src.core.modules.project_management.domain.risk.register import RegisterEntryType

    entry = services["register_service"].create_entry(
        project.id, entry_type=RegisterEntryType.ISSUE, title="P41-FIX issue"
    )
    controller = platform_catalog.controlWorkspace
    controller.ensureLoaded()
    refresh_calls: list[str] = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    services["register_service"].update_entry(
        entry.id, expected_version=entry.version, title="P41-FIX issue updated"
    )
    services["register_service"].delete_entry(entry.id)

    assert refresh_calls == ["refresh", "refresh"]


def test_control_does_not_refresh_from_an_unrelated_view_invalidation_category(services):
    _platform_catalog, pm_catalog = _wire_catalogs(services)
    stale_calls: list[str] = []
    pm_catalog.registerWorkspaceStale.connect(lambda project_id: stale_calls.append(project_id))

    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        "P41-FIX unrelated budget project", financial_currency_code=organization.base_currency
    )
    services["budget_service"].create_budget(project.id, "P41-FIX unrelated budget")

    assert stale_calls == [], (
        "a Budget-only mutation (a different ViewInvalidation category) must not fire the "
        "Register-scoped cross-layer signal"
    )

    from src.core.modules.project_management.domain.risk.register import RegisterEntryType

    services["register_service"].create_entry(
        project.id, entry_type=RegisterEntryType.RISK, title="P41-FIX category-proof risk"
    )

    assert stale_calls == [project.id], "the same signal fires for an actual Register mutation"


def test_legacy_register_signal_remains_absent_after_the_fix():
    from src.core.shared.events.domain_events import domain_events

    assert not hasattr(domain_events, "register_changed")
