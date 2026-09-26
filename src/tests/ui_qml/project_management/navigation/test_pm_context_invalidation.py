"""PM's context-level invalidation safety net: `refreshContextAvailability`
re-validates the current workspace selection against a supplied accessible
set and redirects to a safe destination when the current one is no longer
present. PM's context navigation is not filtered by permissions today (a
documented product decision), so nothing calls this in production yet -- it
exists so a future Level-2 PM accessibility source can plug in through the
same redirect contract Platform already uses."""

from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common.pm_workspace_navigation_controller import (
    PMWorkspaceNavigationController,
)
from src.ui_qml.modules.project_management.navigation import PM_WORKSPACE_KEYS


def test_redirects_to_dashboard_when_current_workspace_becomes_unavailable():
    controller = PMWorkspaceNavigationController()
    controller.selectWorkspace("review_queue")
    assert controller.workspaceKey == "review_queue"

    remaining = [key for key in PM_WORKSPACE_KEYS if key != "review_queue"]
    controller.refreshContextAvailability(remaining)

    assert controller.workspaceKey == "dashboard"


def test_current_workspace_is_left_unchanged_when_still_accessible():
    controller = PMWorkspaceNavigationController()
    controller.selectWorkspace("tasks")

    controller.refreshContextAvailability(list(PM_WORKSPACE_KEYS))

    assert controller.workspaceKey == "tasks"


def test_redirect_prefers_dashboard_over_any_other_still_accessible_workspace():
    controller = PMWorkspaceNavigationController()
    controller.selectWorkspace("review_queue")

    # Both "dashboard" and "resources" remain accessible -- dashboard (the
    # PM Overview) must be preferred.
    controller.refreshContextAvailability(["dashboard", "resources"])

    assert controller.workspaceKey == "dashboard"


def test_empty_accessible_set_is_a_no_op():
    """An empty/unset accessible list means "no filtering data available" --
    fail safe by doing nothing, rather than redirecting away from a
    perfectly valid destination on missing data."""
    controller = PMWorkspaceNavigationController()
    controller.selectWorkspace("projects")

    controller.refreshContextAvailability([])

    assert controller.workspaceKey == "projects"
