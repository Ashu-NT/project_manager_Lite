from __future__ import annotations

import glob
import inspect

from src.application.runtime import build_desktop_api_registry
from src.core.shared.events.domain_events import domain_events
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


def test_costs_changed_signal_no_longer_exists():
    assert not hasattr(domain_events, "costs_changed")


def test_calendars_changed_signal_no_longer_exists():
    assert not hasattr(domain_events, "calendars_changed")


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


def test_approval_service_reflective_emission_mechanism_is_real_and_active():
    import src.core.platform.application.approval.approval_service as approval_service_module

    source = inspect.getsource(approval_service_module)
    assert "_emit_signal_safely" in source
    assert "getattr(domain_events, signal_name" in source


# ---------------------------------------------------------------------------
# 3. Consumer subscriptions removed -- verified via real end-to-end refresh behavior
# ---------------------------------------------------------------------------


def test_pm_dashboard_no_longer_reacts_to_costs_changed_because_it_no_longer_exists(services):
    _pm_catalog(services)
    assert not hasattr(domain_events, "costs_changed")



def test_pm_financials_workspace_coalesces_scoped_finance_invalidations(services, qapp):
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.financialsWorkspace
    project_id = _unique("p7b-finance-project")
    controller._set_selected_project_id(project_id)
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    domain_events.project_changed.emit(project_id)
    domain_events.tasks_changed.emit(project_id)

    qapp.processEvents()

    assert refresh_calls == ["refresh"]


def test_pm_portfolio_workspace_still_reacts_to_its_remaining_real_signals(services, qapp):
    """P42: was `portfolio_changed` -- deleted (Portfolio fully modernized). This test's own
    purpose was always "Portfolio workspace still reacts to at least one of its surviving legacy
    Signal subscriptions," not specifically its own capability's typed facts (proved separately,
    end to end with real services, by `test_p42_portfolio_full_modernization.py`) -- so
    repointing to `project_changed`, Portfolio's other remaining legacy subscription, preserves
    that intent exactly."""
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.portfolioWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    domain_events.project_changed.emit(_unique("p7b-portfolio"))
    from PySide6.QtWidgets import QApplication

    QApplication.processEvents()

    assert refresh_calls == ["refresh"]


def test_control_workspace_still_reacts_to_its_remaining_real_signals(services):
    catalog = _catalog(services)
    controller = catalog.controlWorkspace
    controller.ensureLoaded()
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    domain_events.tasks_changed.emit(_unique("p7b-tasks"))

    assert refresh_calls == ["refresh"]


def test_admin_console_still_reacts_to_its_remaining_signal(services):
    catalog = _catalog(services)
    admin = catalog.adminWorkspace
    refresh_calls = []
    admin.refresh = lambda: refresh_calls.append("refresh") or None

    domain_events.auth_changed.emit(_unique("p7b-auth"))

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
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    domain_events.project_changed.emit(_unique("p7b-sched-project"))
    domain_events.tasks_changed.emit(_unique("p7b-sched-tasks"))
    services["resource_service"].create_resource(name=_unique("p7b-sched-resource"))

    assert refresh_calls == ["refresh"] * 3


# ---------------------------------------------------------------------------
# 4. No replacement, no reintroduction, no invented events
# ---------------------------------------------------------------------------


def test_no_new_business_domain_event_or_replacement_signal_introduced():
    import dataclasses

    signal_names = [f.name for f in dataclasses.fields(domain_events)]
    assert "costs_changed" not in signal_names
    assert "calendars_changed" not in signal_names

    reference_counts = {name: 0 for name in signal_names}
    for path in _production_source_files():
        if path == "src/core/shared/events/domain_events.py":
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = _strip_strings_and_comments(fh.read())
        for name in signal_names:
            if name in source:
                reference_counts[name] += 1

    orphaned = [name for name, count in reference_counts.items() if count == 0]
    assert orphaned == [], orphaned


def test_domain_event_binder_still_kept_unchanged_in_responsibility():
    import src.ui_qml.platform.controllers.admin_console.domain_event_binder as binder_module

    source = _strip_strings_and_comments(inspect.getsource(binder_module))
    for forbidden in (
        "_subscribe_domain_change", "domain_changed", "_BRIDGE_SPECS", "calendars_changed",
        "organizations_changed", "employees_changed", "departments_changed", "sites_changed",
        "parties_changed", "documents_changed",
    ):
        assert forbidden not in source
    for still_present in (
        "auth_changed",
    ):
        assert still_present in source


def test_organizations_changed_field_no_longer_exists():
    assert not hasattr(domain_events, "organizations_changed")

    import src.core.platform.application.master_data.org.organization_service as org_service_module

    source = inspect.getsource(org_service_module)
    assert "organizations_changed" not in source
    assert "domain_events" not in source
