"""R2.1 characterization tests for the pre-existing, committed-but-inert R2
scaffolding: navigation.py and PMWorkspaceNavigationController. These freeze
CURRENT behavior before any wiring/integration work touches them -- do not
"fix" surprising behavior found here without deliberately deciding to
change it in a later R2 stage."""

from __future__ import annotations

from src.ui_qml.modules.project_management.navigation import (
    PM_CANONICAL_ROUTE_ID,
    PM_COMPATIBILITY_ROUTE_IDS,
    PM_WORKSPACE_KEYS,
    PMWorkspaceIntent,
    compatibility_route_intent,
    workspace_intent,
)
from src.ui_qml.modules.project_management.controllers.common.pm_workspace_navigation_controller import (
    PMWorkspaceNavigationController,
)


def _signal_counter(signal):
    counts = {"n": 0}
    signal.connect(lambda *_args: counts.__setitem__("n", counts["n"] + 1))
    return counts


# ---------------------------------------------------------------------------
# navigation.py
# ---------------------------------------------------------------------------


def test_pm_canonical_route_id_value():
    assert PM_CANONICAL_ROUTE_ID == "project_management.workspace"


def test_pm_workspace_keys_cover_the_eleven_current_capabilities():
    assert set(PM_WORKSPACE_KEYS) == {
        "dashboard",
        "portfolio",
        "projects",
        "tasks",
        "scheduling",
        "resources",
        "timesheets",
        "review_queue",
        "financials",
        "register",
        "collaboration",
    }
    assert len(PM_WORKSPACE_KEYS) == 11


def test_pm_compatibility_route_ids_are_prefixed_workspace_keys():
    assert set(PM_COMPATIBILITY_ROUTE_IDS) == {
        f"project_management.{key}"
        for key in PM_WORKSPACE_KEYS
        if key != "review_queue"
    }
    assert "project_management.review_queue" not in PM_COMPATIBILITY_ROUTE_IDS
    assert PM_CANONICAL_ROUTE_ID not in PM_COMPATIBILITY_ROUTE_IDS


def test_all_current_workspace_mappings_match_target_destinations():
    expected = {
        "dashboard": ("overview", ""),
        "portfolio": ("portfolio", ""),
        "projects": ("work", "projects"),
        "tasks": ("work", "tasks"),
        "scheduling": ("work", "planning"),
        "resources": ("workload", "resources"),
        "timesheets": ("work", "timesheets"),
        "review_queue": ("workload", "review_queue"),
        "financials": ("finance", ""),
        "register": ("governance", "register"),
        "collaboration": ("governance", "collaboration"),
    }
    for key, (destination_id, secondary_id) in expected.items():
        intent = workspace_intent(key)
        assert intent is not None, key
        assert intent.workspace_key == key
        assert intent.destination_id == destination_id
        assert intent.secondary_id == secondary_id


def test_workspace_intent_invalid_or_empty_key_returns_none():
    assert workspace_intent("") is None
    assert workspace_intent(None) is None
    assert workspace_intent("not-a-real-key") is None
    assert workspace_intent("  ") is None


def test_compatibility_route_intent_translates_legacy_route():
    intent = compatibility_route_intent("project_management.tasks")
    assert intent == PMWorkspaceIntent("work", "tasks", "tasks")


def test_compatibility_route_intent_rejects_canonical_route():
    assert compatibility_route_intent(PM_CANONICAL_ROUTE_ID) is None


def test_compatibility_route_intent_rejects_unrelated_or_unknown_route():
    assert compatibility_route_intent("platform.workspace") is None
    assert compatibility_route_intent("project_management.nonexistent") is None
    assert compatibility_route_intent("") is None
    assert compatibility_route_intent(None) is None


# ---------------------------------------------------------------------------
# PMWorkspaceNavigationController
# ---------------------------------------------------------------------------


def test_navigation_default_destination_is_dashboard_overview():
    controller = PMWorkspaceNavigationController()

    assert controller.workspaceKey == "dashboard"
    assert controller.destinationId == "overview"
    assert controller.secondaryId == ""


def test_navigation_items_cover_all_eleven_workspaces_in_six_groups():
    controller = PMWorkspaceNavigationController()
    items = controller.navigationItems

    assert len(items) == 11
    ids = {item["id"] for item in items}
    assert ids == set(PM_WORKSPACE_KEYS)

    groups: dict[str, list[str]] = {}
    for item in items:
        groups.setdefault(item["group"], []).append(item["id"])

    assert set(groups) == {
        "Overview",
        "Portfolio",
        "Work",
        "Workload Management",
        "Finance",
        "Governance",
    }
    assert sorted(groups["Overview"]) == ["dashboard"]
    assert sorted(groups["Portfolio"]) == ["portfolio"]
    assert sorted(groups["Work"]) == ["projects", "scheduling", "tasks", "timesheets"]
    assert sorted(groups["Workload Management"]) == ["resources", "review_queue"]
    assert sorted(groups["Finance"]) == ["financials"]
    assert sorted(groups["Governance"]) == ["collaboration", "register"]


def test_select_workspace_valid_key_updates_selection_and_emits():
    controller = PMWorkspaceNavigationController()
    selection_changed = _signal_counter(controller.selectionChanged)
    route_changed = _signal_counter(controller.routeStateChanged)

    result = controller.selectWorkspace("tasks")

    assert result is True
    assert controller.workspaceKey == "tasks"
    assert controller.destinationId == "work"
    assert controller.secondaryId == "tasks"
    assert selection_changed["n"] == 1
    assert route_changed["n"] == 1


def test_select_workspace_invalid_key_is_rejected():
    controller = PMWorkspaceNavigationController()
    selection_changed = _signal_counter(controller.selectionChanged)

    result = controller.selectWorkspace("not-a-workspace")

    assert result is False
    assert controller.workspaceKey == "dashboard"
    assert selection_changed["n"] == 0


def test_select_workspace_same_key_does_not_reemit_selection_changed():
    controller = PMWorkspaceNavigationController()
    controller.selectWorkspace("tasks")
    selection_changed = _signal_counter(controller.selectionChanged)
    route_changed = _signal_counter(controller.routeStateChanged)

    result = controller.selectWorkspace("tasks")

    assert result is True
    assert selection_changed["n"] == 0
    assert route_changed["n"] == 0


def test_open_entity_sets_workspace_entity_and_section():
    controller = PMWorkspaceNavigationController()
    route_changed = _signal_counter(controller.routeStateChanged)

    result = controller.openEntity("tasks", "TSK-208", "time")

    assert result is True
    assert controller.workspaceKey == "tasks"
    assert controller.routeState == {
        "routeId": PM_CANONICAL_ROUTE_ID,
        "destination": "work",
        "workspaceKey": "tasks",
        "secondary": "tasks",
        "entityId": "TSK-208",
        "section": "time",
    }
    assert route_changed["n"] >= 1


def test_open_entity_invalid_workspace_key_is_rejected():
    controller = PMWorkspaceNavigationController()

    result = controller.openEntity("not-a-workspace", "TSK-208")

    assert result is False
    assert controller.workspaceKey == "dashboard"


def test_apply_route_canonical_id_is_a_no_op_success():
    controller = PMWorkspaceNavigationController()
    controller.selectWorkspace("tasks")

    result = controller.applyRoute(PM_CANONICAL_ROUTE_ID)

    assert result is True
    assert controller.workspaceKey == "tasks"


def test_apply_route_legacy_route_selects_matching_workspace():
    controller = PMWorkspaceNavigationController()

    result = controller.applyRoute("project_management.scheduling")

    assert result is True
    assert controller.workspaceKey == "scheduling"
    assert controller.destinationId == "work"
    assert controller.secondaryId == "planning"


def test_apply_route_unknown_route_is_rejected():
    controller = PMWorkspaceNavigationController()

    result = controller.applyRoute("project_management.nonexistent")

    assert result is False
    assert controller.workspaceKey == "dashboard"


def test_all_current_destinations_are_always_present_in_navigation_items():
    """R2.14: PMCapabilityController's existing R1.8 facts (canApproveBaseline,
    canApplyLeveling, canManageSkills, canRequestAssignmentOverride, canImport,
    canApprovePmRequest) are all fine-grained ACTION-level permissions, not a
    per-destination "can you see this workspace" contract. No such contract
    exists yet, so R2 deliberately does not filter navigationItems by
    capability -- doing so would mean inventing a destination->capability
    mapping with no backing product decision, which this modernization
    effort has consistently avoided elsewhere (e.g. no invented Rebalance,
    no invented Purchase Orders). This test freezes that as an explicit,
    verified statement rather than a silent gap."""
    controller = PMWorkspaceNavigationController()

    ids = {item["id"] for item in controller.navigationItems}
    assert ids == set(PM_WORKSPACE_KEYS)
