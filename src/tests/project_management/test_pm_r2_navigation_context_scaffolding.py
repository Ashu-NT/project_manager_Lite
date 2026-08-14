"""R2.1 characterization tests for the pre-existing, committed-but-inert R2
scaffolding: navigation.py, PMProjectContextController, and
PMWorkspaceNavigationController. These freeze CURRENT behavior before any
wiring/integration work touches them -- do not "fix" surprising behavior
found here without deliberately deciding to change it in a later R2 stage."""

from __future__ import annotations

from src.ui_qml.modules.project_management.navigation import (
    PM_CANONICAL_ROUTE_ID,
    PM_COMPATIBILITY_ROUTE_IDS,
    PM_WORKSPACE_KEYS,
    PMWorkspaceIntent,
    ProjectContextPolicy,
    compatibility_route_intent,
    workspace_intent,
)
from src.ui_qml.modules.project_management.controllers.common.pm_project_context_controller import (
    PMProjectContextController,
)
from src.ui_qml.modules.project_management.controllers.common.pm_workspace_navigation_controller import (
    PMWorkspaceNavigationController,
)


class _FakeProject:
    def __init__(self, project_id: str, name: str, code: str = "", status_label: str = "Active") -> None:
        self.id = project_id
        self.name = name
        self.code = code
        self.status_label = status_label


class _FakePage:
    def __init__(self, items):
        self.items = items


class _FakeProjectsApi:
    def __init__(self, projects):
        self._projects = {project.id: project for project in projects}

    def list_project_page(self, *, search_text="", **_kwargs):
        needle = str(search_text or "").casefold()
        items = [p for p in self._projects.values() if needle in p.name.casefold()]
        return _FakePage(items)

    def get_project(self, project_id):
        return self._projects.get(str(project_id or ""))


def _signal_counter(signal):
    counts = {"n": 0}
    signal.connect(lambda *_args: counts.__setitem__("n", counts["n"] + 1))
    return counts


# ---------------------------------------------------------------------------
# navigation.py
# ---------------------------------------------------------------------------


def test_pm_canonical_route_id_value():
    assert PM_CANONICAL_ROUTE_ID == "project_management.workspace"


def test_pm_workspace_keys_are_exactly_the_ten_legacy_capabilities():
    assert set(PM_WORKSPACE_KEYS) == {
        "dashboard",
        "portfolio",
        "projects",
        "tasks",
        "scheduling",
        "resources",
        "timesheets",
        "financials",
        "register",
        "collaboration",
    }
    assert len(PM_WORKSPACE_KEYS) == 10


def test_pm_compatibility_route_ids_are_prefixed_workspace_keys():
    assert set(PM_COMPATIBILITY_ROUTE_IDS) == {
        f"project_management.{key}" for key in PM_WORKSPACE_KEYS
    }
    assert PM_CANONICAL_ROUTE_ID not in PM_COMPATIBILITY_ROUTE_IDS


def test_all_ten_legacy_workspace_mappings_match_target_destinations():
    expected = {
        "dashboard": ("overview", ""),
        "portfolio": ("portfolio", ""),
        "projects": ("work", "projects"),
        "tasks": ("work", "tasks"),
        "scheduling": ("work", "planning"),
        "resources": ("workload", "resources"),
        "timesheets": ("workload", "review_queue"),
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


def test_workspace_intent_project_context_policy_matches_approved_table():
    # R2.9 approved per-destination policy table.
    expected_policy = {
        "dashboard": ProjectContextPolicy.OPTIONAL,
        "portfolio": ProjectContextPolicy.NOT_APPLICABLE,
        "projects": ProjectContextPolicy.NOT_APPLICABLE,
        "tasks": ProjectContextPolicy.OPTIONAL,
        "scheduling": ProjectContextPolicy.REQUIRED,
        "resources": ProjectContextPolicy.OPTIONAL,
        "timesheets": ProjectContextPolicy.OPTIONAL,
        "financials": ProjectContextPolicy.REQUIRED,
        "register": ProjectContextPolicy.OPTIONAL,
        "collaboration": ProjectContextPolicy.OPTIONAL,
    }
    for key, policy in expected_policy.items():
        intent = workspace_intent(key)
        assert intent is not None, key
        assert intent.project_context_policy == policy, key


def test_project_context_policy_enum_values_are_plain_strings():
    assert ProjectContextPolicy.REQUIRED.value == "required"
    assert ProjectContextPolicy.OPTIONAL.value == "optional"
    assert ProjectContextPolicy.NOT_APPLICABLE.value == "not_applicable"


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
# PMProjectContextController
# ---------------------------------------------------------------------------


def test_project_context_default_state_without_api():
    controller = PMProjectContextController()

    assert controller.activeProjectId == ""
    assert controller.activeProjectLabel == ""
    assert controller.hasActiveProject is False
    assert controller.projectOptions == []
    assert controller.validationStatus == "unavailable"
    assert controller.errorMessage == ""


def test_project_context_default_state_with_api_is_ready():
    controller = PMProjectContextController(projects_api=_FakeProjectsApi([]))

    assert controller.validationStatus == "ready"
    assert controller.hasActiveProject is False


def test_select_project_valid_id_sets_active_project():
    api = _FakeProjectsApi([_FakeProject("p-1", "Plant Upgrade")])
    controller = PMProjectContextController(projects_api=api)
    changed = _signal_counter(controller.activeProjectChanged)

    result = controller.selectProject("p-1")

    assert result is True
    assert controller.activeProjectId == "p-1"
    assert controller.activeProjectLabel == "Plant Upgrade"
    assert controller.hasActiveProject is True
    assert controller.validationStatus == "ready"
    assert changed["n"] == 1


def test_select_project_unknown_id_is_rejected_as_stale():
    api = _FakeProjectsApi([_FakeProject("p-1", "Plant Upgrade")])
    controller = PMProjectContextController(projects_api=api)

    result = controller.selectProject("does-not-exist")

    assert result is False
    assert controller.hasActiveProject is False
    assert controller.validationStatus == "stale"
    assert controller.errorMessage != ""


def test_select_project_without_api_is_rejected_as_stale():
    """Characterizes CURRENT behavior: a missing projects_api makes any
    selectProject() call resolve as "stale" (same code path as an unknown
    ID), not a distinct "unavailable" outcome. Documented as a known rough
    edge in the R2 closure report rather than silently changed here."""
    controller = PMProjectContextController(projects_api=None)

    result = controller.selectProject("p-1")

    assert result is False
    assert controller.hasActiveProject is False
    assert controller.validationStatus == "stale"


def test_clear_project_resets_active_project():
    api = _FakeProjectsApi([_FakeProject("p-1", "Plant Upgrade")])
    controller = PMProjectContextController(projects_api=api)
    controller.selectProject("p-1")

    controller.clearProject()

    assert controller.activeProjectId == ""
    assert controller.activeProjectLabel == ""
    assert controller.hasActiveProject is False
    assert controller.validationStatus == "ready"


def test_clear_project_without_api_reports_unavailable():
    controller = PMProjectContextController(projects_api=None)

    controller.clearProject()

    assert controller.validationStatus == "unavailable"


def test_open_project_emits_intent_signal_without_pinning_context():
    api = _FakeProjectsApi([_FakeProject("p-1", "Plant Upgrade")])
    controller = PMProjectContextController(projects_api=api)
    received = []
    controller.projectOpenRequested.connect(lambda pid, route: received.append((pid, route)))

    result = controller.openProject("p-1", "projects_list")

    assert result is True
    assert received == [("p-1", "projects_list")]
    # Critical R2.10 invariant: opening a project is a navigation/detail
    # intent only. It must NEVER pin the shared active-project context.
    assert controller.activeProjectId == ""
    assert controller.hasActiveProject is False


def test_open_project_unknown_id_does_not_emit_and_marks_stale():
    api = _FakeProjectsApi([_FakeProject("p-1", "Plant Upgrade")])
    controller = PMProjectContextController(projects_api=api)
    received = []
    controller.projectOpenRequested.connect(lambda pid, route: received.append((pid, route)))

    result = controller.openProject("missing", "projects_list")

    assert result is False
    assert received == []
    assert controller.validationStatus == "stale"


def test_revalidate_with_no_active_project_is_a_no_op_success():
    controller = PMProjectContextController(projects_api=_FakeProjectsApi([]))

    assert controller.revalidate() is True
    assert controller.hasActiveProject is False


def test_revalidate_preserves_still_accessible_active_project():
    api = _FakeProjectsApi([_FakeProject("p-1", "Plant Upgrade")])
    controller = PMProjectContextController(projects_api=api)
    controller.selectProject("p-1")

    assert controller.revalidate() is True
    assert controller.activeProjectId == "p-1"
    assert controller.validationStatus == "ready"


def test_revalidate_clears_project_that_became_inaccessible():
    api = _FakeProjectsApi([_FakeProject("p-1", "Plant Upgrade")])
    controller = PMProjectContextController(projects_api=api)
    controller.selectProject("p-1")
    # Simulate the project becoming inaccessible (e.g. tenant/org switch).
    api._projects.clear()

    assert controller.revalidate() is False
    assert controller.hasActiveProject is False
    assert controller.activeProjectId == ""
    assert controller.validationStatus == "stale"


def test_reset_context_clears_project_and_reloads_options():
    api = _FakeProjectsApi([_FakeProject("p-1", "Plant Upgrade"), _FakeProject("p-2", "Harbor Expansion")])
    controller = PMProjectContextController(projects_api=api)
    controller.selectProject("p-1")

    controller.resetContext()

    assert controller.hasActiveProject is False
    assert len(controller.projectOptions) == 2


def test_refresh_and_search_projects_serialize_expected_option_shape():
    api = _FakeProjectsApi([_FakeProject("p-1", "Plant Upgrade", code="PRJ-1", status_label="Active")])
    controller = PMProjectContextController(projects_api=api)

    controller.refreshProjects()

    assert controller.projectOptions == [
        {"id": "p-1", "label": "Plant Upgrade", "code": "PRJ-1", "statusLabel": "Active"}
    ]

    controller.searchProjects("nothing matches")
    assert controller.projectOptions == []


# ---------------------------------------------------------------------------
# PMWorkspaceNavigationController
# ---------------------------------------------------------------------------


def test_navigation_default_destination_is_dashboard_overview():
    controller = PMWorkspaceNavigationController()

    assert controller.workspaceKey == "dashboard"
    assert controller.destinationId == "overview"
    assert controller.secondaryId == ""
    assert controller.projectContextPolicy == "optional"


def test_navigation_project_context_policy_follows_selected_workspace():
    controller = PMWorkspaceNavigationController()

    controller.selectWorkspace("scheduling")
    assert controller.projectContextPolicy == "required"

    controller.selectWorkspace("portfolio")
    assert controller.projectContextPolicy == "not_applicable"

    controller.selectWorkspace("financials")
    assert controller.projectContextPolicy == "required"


def test_navigation_items_cover_all_ten_workspaces_in_six_groups():
    controller = PMWorkspaceNavigationController()
    items = controller.navigationItems

    assert len(items) == 10
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
    assert sorted(groups["Work"]) == ["projects", "scheduling", "tasks"]
    assert sorted(groups["Workload Management"]) == ["resources", "timesheets"]
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


def test_all_ten_destinations_are_always_present_in_navigation_items():
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
