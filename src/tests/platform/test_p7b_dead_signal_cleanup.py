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


# P46B: `test_costs_changed_signal_no_longer_exists`/`test_calendars_changed_signal_no_longer_
# exists` (standalone `hasattr(domain_events, ...)` checks) removed -- `domain_events` module is
# deleted outright; the stronger source-string guard below independently proves zero production
# references for both names.


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
    """Superseded by P45B: Task modernization was the reflective bridge's last remaining
    production caller, so `_emit_signal_safely` is now deleted outright (see
    test_p7c_zero_consumer_signal_cleanup.py's own updated assertion)."""
    import src.core.platform.application.approval.approval_service as approval_service_module

    source = inspect.getsource(approval_service_module)
    assert "_emit_signal_safely" not in source


# ---------------------------------------------------------------------------
# 3. Consumer subscriptions removed -- verified via real end-to-end refresh behavior
# ---------------------------------------------------------------------------


def test_pm_financials_workspace_coalesces_scoped_finance_invalidations(services, qapp):
    """P43: was `domain_events.project_changed.emit(...)` (deleted -- Project fully modernized
    onto typed DomainEvents + `ProjectViewInvalidationAdapter`). P45B: `tasks_changed` is also
    deleted -- Financials' remaining Task dependency is now delivered via
    `_financials_task_view_invalidation_adapter.taskScheduleStale`."""
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
    """P42: was `portfolio_changed` -- deleted (Portfolio fully modernized). P43: was
    `project_changed` -- also deleted (Project fully modernized). This test's own purpose was
    always "Portfolio workspace still reacts to at least one of its surviving legacy Signal
    subscriptions," not specifically its own capability's typed facts (proved separately, end to
    end with real services, by `test_p42_portfolio_full_modernization.py`) -- P45B deleted
    `tasks_changed` too, so repointing to `taskListStale` (Portfolio's one remaining Task
    dependency, via `_portfolio_task_view_invalidation_adapter`) preserves that intent exactly."""
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.portfolioWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    pm_catalog._portfolio_task_view_invalidation_adapter.taskListStale.emit(_unique("p7b-portfolio"))
    from PySide6.QtWidgets import QApplication

    QApplication.processEvents()

    assert refresh_calls == ["refresh"]


def test_control_workspace_still_reacts_to_its_remaining_real_signals(services):
    """P45B: `tasks_changed` is deleted -- Platform Control's real dependency is now delivered
    via `ProjectManagementWorkspaceCatalog.taskWorkspaceActivityStale`, connected in `app.py` to
    this same generic `onExternalViewStale` slot (neither side imports the other's
    implementation). Calling the slot directly proves the property without full app-level
    cross-catalog wiring in this unit test."""
    catalog = _catalog(services)
    controller = catalog.controlWorkspace
    controller.ensureLoaded()
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    controller.onExternalViewStale(_unique("p7b-tasks"))

    assert refresh_calls == ["refresh"]


# P46B: `test_admin_console_still_reacts_to_its_remaining_signal` used `domain_events.auth_changed`
# as the admin console's one remaining legacy-signal dependency -- Auth/Security is now fully
# modernized, `admin_console/domain_event_binder.py` (the coarse composite refresher this test
# exercised) is deleted outright, and the admin console instead reacts to the narrow
# `refresh_users`/`refresh_after_account_security_change` targets. See
# `test_zero_auth_changed_subscribers_remain` in test_p5_closeout_auth_changed_audit.py and
# `test_platform_admin_access_workspace_reacts_to_account_security_change_narrowly` in
# test_qml_domain_event_bridges_pm.py for the current coverage.


def test_pm_resources_workspace_still_reacts_to_resources(services):
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.resourcesWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    services["resource_service"].create_resource(name=_unique("p7b-resource"))

    assert refresh_calls == ["refresh"]


def test_pm_scheduling_workspace_still_reacts_to_its_remaining_real_signals(services):
    """P43: was `domain_events.project_changed.emit(...)` (deleted -- Project fully modernized
    onto typed DomainEvents + `ProjectViewInvalidationAdapter`). P45B: `tasks_changed` is also
    deleted -- Scheduling's remaining Task dependency is now delivered via
    `_scheduling_task_view_invalidation_adapter.taskScheduleStale`."""
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


# P46B: `test_no_new_business_domain_event_or_replacement_signal_introduced` (an orphan-detection
# loop over `dataclasses.fields(domain_events)`) removed -- `domain_events` module is deleted
# outright, and since it permanently carries zero fields (see test_p8_platform_event_architecture_
# canonicalization.py's `_current_signal_names`), the "every current signal has a production
# reference" invariant it checked is now vacuously and permanently true.


# P46B: `test_domain_event_binder_still_kept_unchanged_in_responsibility` imported
# `admin_console/domain_event_binder.py`, which is now deleted outright (it was 100%
# `auth_changed`-specific composite-refresh coordination; see
# test_p5_closeout_auth_changed_audit.py's `test_zero_auth_changed_subscribers_remain`).


def test_organizations_changed_field_no_longer_exists():
    import src.core.platform.application.master_data.org.organization_service as org_service_module

    source = inspect.getsource(org_service_module)
    assert "organizations_changed" not in source
    assert "domain_events" not in source
