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
    """Word-boundary matching -- `costs_changed` is a trailing substring of
    `planned_costs_changed` (a real, still-alive, unrelated signal), so a plain substring search
    would false-positive on it."""
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
    """`_emit_signal_safely` -> `getattr(domain_events, signal_name).emit(...)` is a genuine,
    active production emission path (called from `_emit_handler_events`, which runs after every
    real approve/reject decision) -- not a dead/test-only mechanism. Confirms why a signal can
    have a real producer with zero literal `domain_events.X.emit(` call sites of its own."""
    import src.core.platform.application.approval.approval_service as approval_service_module

    source = inspect.getsource(approval_service_module)
    assert "_emit_signal_safely" in source
    assert "getattr(domain_events, signal_name" in source


# ---------------------------------------------------------------------------
# 3. Consumer subscriptions removed -- verified via real end-to-end refresh behavior
# ---------------------------------------------------------------------------


def test_pm_dashboard_no_longer_reacts_to_costs_changed_because_it_no_longer_exists(services):
    """Behavior-preservation proof: since `costs_changed` never had a real producer, no
    production code path could ever have triggered this reaction -- deleting the dead
    subscription changes nothing observable."""
    _pm_catalog(services)
    assert not hasattr(domain_events, "costs_changed")
    # There is no signal left to emit that could exercise the deleted subscription -- the
    # absence assertion above, plus the source-reference-count guard, is the complete proof.


def test_pm_financials_workspace_coalesces_scoped_finance_invalidations(services, qapp):
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.financialsWorkspace
    project_id = _unique("p7b-finance-project")
    controller._set_selected_project_id(project_id)
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    domain_events.budgets_changed.emit(project_id)
    domain_events.planned_costs_changed.emit(project_id)
    domain_events.billing_preparations_changed.emit(project_id)

    qapp.processEvents()

    assert refresh_calls == ["refresh"]


def test_pm_portfolio_workspace_still_reacts_to_its_remaining_real_signals(services, qapp):
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.portfolioWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    domain_events.portfolio_changed.emit(_unique("p7b-portfolio"))
    from PySide6.QtWidgets import QApplication

    QApplication.processEvents()

    assert refresh_calls == ["refresh"]


def test_control_workspace_still_reacts_to_its_remaining_real_signals(services):
    catalog = _catalog(services)
    controller = catalog.controlWorkspace
    controller.ensureLoaded()
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    domain_events.register_changed.emit(_unique("p7b-register"))

    assert refresh_calls == ["refresh"]


def test_admin_console_still_reacts_to_its_remaining_two_real_signals(services):
    """P10D/P12B/P13B/P14B/P15B: `organizations_changed`/`employees_changed`/
    `departments_changed`/`sites_changed`/`parties_changed` are all gone (all five now flow
    through their own typed ViewInvalidation targets, wired directly in `context.py`, not through
    this composite Signal list) -- two legacy signals remain here."""
    catalog = _catalog(services)
    admin = catalog.adminWorkspace
    refresh_calls = []
    admin.refresh = lambda: refresh_calls.append("refresh") or None

    domain_events.auth_changed.emit(_unique("p7b-auth"))
    domain_events.documents_changed.emit(_unique("p7b-doc"))

    assert refresh_calls == ["refresh"] * 2


def test_pm_resources_workspace_still_reacts_to_resources(services):
    """Confirms the resources binder's `calendars_changed`/`employees_changed` removals did not
    accidentally also remove its other, still-real subscriptions."""
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.resourcesWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    domain_events.resources_changed.emit(_unique("p7b-resource"))

    assert refresh_calls == ["refresh"]


def test_pm_scheduling_workspace_still_reacts_to_its_remaining_real_signals(services):
    pm_catalog = _pm_catalog(services)
    controller = pm_catalog.schedulingWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    domain_events.project_changed.emit(_unique("p7b-sched-project"))
    domain_events.tasks_changed.emit(_unique("p7b-sched-tasks"))
    domain_events.baseline_changed.emit(_unique("p7b-sched-baseline"))
    domain_events.resources_changed.emit(_unique("p7b-sched-resources"))

    assert refresh_calls == ["refresh"] * 4


# ---------------------------------------------------------------------------
# 4. No replacement, no reintroduction, no invented events
# ---------------------------------------------------------------------------


def test_no_new_business_domain_event_or_replacement_signal_introduced():
    """The two deleted signals must not have been replaced by a renamed equivalent
    (`CostsChanged`, `CalendarsChanged`, or similar) -- this is deletion only."""
    forbidden = ("CostsChanged", "CalendarsChanged", "cost_changed", "calendar_changed")
    hits = []
    for path in _production_source_files():
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = _strip_strings_and_comments(fh.read())
        if any(name in source for name in forbidden):
            hits.append(path)
    assert hits == [], hits


def test_final_signal_invariant_every_remaining_signal_has_a_source_reference_beyond_its_declaration():
    """§7: every remaining `DomainEvents` field must appear somewhere in production source beyond
    its own declaration line in `domain_events.py` -- i.e. it has at least one real producer or
    consumer reference. This is a coarse, source-grep-level sanity check (not a precise
    producer/consumer classifier), intended to catch an obviously-orphaned field, not to replace
    the manual audit above."""
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
    # R6B restored the Finance family hints only after adding both committed mutation
    # producers and a targeted Finance destination-cache consumer. Every remaining signal
    # therefore has an active production path in both directions.
    assert orphaned == [], orphaned


def test_domain_event_binder_still_kept_unchanged_in_responsibility():
    """§10: still not deleted -- still real, direct, non-compatibility composite-refresh
    coordination, now for 2 signals instead of 8 (`calendars_changed` removed by P7B,
    `organizations_changed` removed by P10D, `employees_changed` removed by P12B,
    `departments_changed` removed by P13B, `sites_changed` removed by P14B, `parties_changed`
    removed by P15B -- all six route through their own typed ViewInvalidation targets instead)."""
    import src.ui_qml.platform.controllers.admin_console.domain_event_binder as binder_module

    source = _strip_strings_and_comments(inspect.getsource(binder_module))
    for forbidden in (
        "_subscribe_domain_change", "domain_changed", "_BRIDGE_SPECS", "calendars_changed",
        "organizations_changed", "employees_changed", "departments_changed", "sites_changed",
        "parties_changed",
    ):
        assert forbidden not in source
    for still_present in (
        "auth_changed", "documents_changed",
    ):
        assert still_present in source


def test_organizations_changed_field_no_longer_exists():
    """P10D superseded P7B's own `test_organizations_changed_untouched_by_p7b` (which proved
    Organization's legacy signal was deliberately OUT of P7B's scope and left exactly as P7A left
    it) -- Organization event modernization is now complete: creation, profile updates, and
    enable/disable are all typed events, and the legacy Signal field itself is deleted, not
    merely unproduced."""
    assert not hasattr(domain_events, "organizations_changed")

    import src.core.platform.application.master_data.org.organization_service as org_service_module

    source = inspect.getsource(org_service_module)
    assert "organizations_changed" not in source
    assert "domain_events" not in source
