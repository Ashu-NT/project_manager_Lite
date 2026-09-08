from __future__ import annotations

import glob
import inspect

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.platform.context import PlatformWorkspaceCatalog

_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _catalog(services) -> PlatformWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return PlatformWorkspaceCatalog(desktop_api_registry=registry)


def _pm_catalog(services) -> ProjectManagementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)


def _strip_strings_and_comments(source: str) -> str:
    import re

    no_docstrings = re.sub(r'"""[\s\S]*?"""', "", source)
    no_comments = re.sub(r"#.*", "", no_docstrings)
    return no_comments


def _production_source_files():
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        yield normalized


# ---------------------------------------------------------------------------
# 1. The two deleted signals are gone entirely
# ---------------------------------------------------------------------------


def test_costs_changed_and_calendars_changed_have_zero_production_references():
    import re

    pattern = re.compile(r"(?<![\w.])(costs_changed|calendars_changed)\b")
    hits = []
    for path in _production_source_files():
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = _strip_strings_and_comments(fh.read())
        if pattern.search(source):
            hits.append(path)
    assert hits == [], hits


def test_approval_service_reflective_emission_mechanism_retired_by_task_modernization():
    import src.core.platform.application.approval.approval_service as approval_service_module

    source = inspect.getsource(approval_service_module)
    assert "_emit_signal_safely" not in source


# ---------------------------------------------------------------------------
# 3. Consumer subscriptions removed -- verified via real end-to-end refresh behavior
# ---------------------------------------------------------------------------


def test_pm_financials_workspace_coalesces_scoped_finance_invalidations(services, qapp):
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.financialsWorkspace
    project_id = _unique("p7b-finance-project")
    controller._set_selected_project_id(project_id)
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    pm_catalog._financials_project_view_invalidation_adapter.projectDetailStale.emit(project_id)
    pm_catalog._financials_task_view_invalidation_adapter.taskScheduleStale.emit(project_id)

    qapp.processEvents()

    assert refresh_calls == ["refresh"]


def test_pm_portfolio_workspace_still_reacts_to_its_remaining_real_signals(services, qapp):
    """Portfolio's own typed-event coverage lives in
    test_p42_portfolio_full_modernization.py; this proves only that the workspace reacts to its
    Task dependency (`taskListStale`, via `_portfolio_task_view_invalidation_adapter`)."""
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.portfolioWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    pm_catalog._portfolio_task_view_invalidation_adapter.taskListStale.emit(_unique("p7b-portfolio"))
    from PySide6.QtWidgets import QApplication

    QApplication.processEvents()

    assert refresh_calls == ["refresh"]


def test_control_workspace_still_reacts_to_its_remaining_real_signals(services):
    """Platform Control's Task dependency is delivered via
    `ProjectManagementWorkspaceCatalog.taskWorkspaceActivityStale`, connected in `app.py` to this
    generic `onExternalViewStale` slot (neither side imports the other's implementation). Calling
    the slot directly proves the property without full app-level cross-catalog wiring."""
    catalog = _catalog(services)
    controller = catalog.controlWorkspace
    controller.ensureLoaded()
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    controller.onExternalViewStale(_unique("p7b-tasks"))

    assert refresh_calls == ["refresh"]


def test_pm_resources_workspace_still_reacts_to_resources(services):
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.resourcesWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    services["resource_service"].create_resource(name=_unique("p7b-resource"))

    assert refresh_calls == ["refresh"]


def test_pm_scheduling_workspace_still_reacts_to_its_remaining_real_signals(services):
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.schedulingWorkspace
    scheduling_project_id = _unique("p7b-sched-project")
    controller._selected_project_id = scheduling_project_id
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    pm_catalog._scheduling_project_view_invalidation_adapter.projectListStale.emit(
        _unique("p7b-sched-project")
    )
    pm_catalog._scheduling_task_view_invalidation_adapter.taskScheduleStale.emit(
        scheduling_project_id
    )
    services["resource_service"].create_resource(name=_unique("p7b-sched-resource"))

    assert refresh_calls == ["refresh"] * 3


# ---------------------------------------------------------------------------
# 4. No replacement, no reintroduction, no invented events
# ---------------------------------------------------------------------------


def test_organizations_changed_field_no_longer_exists():
    import src.core.platform.application.master_data.org.organization_service as org_service_module

    source = inspect.getsource(org_service_module)
    assert "organizations_changed" not in source
    assert "domain_events" not in source
