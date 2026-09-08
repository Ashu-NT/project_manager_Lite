from PySide6.QtWidgets import QApplication

from src.ui_qml.modules.project_management.context import (
    ProjectManagementWorkspaceCatalog,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


def test_pm_tasks_workspace_queues_domain_refresh_while_busy(monkeypatch) -> None:
    """P45B: `tasks_changed` is deleted -- the Tasks workspace now reacts to `onTaskListStale`,
    wired via a `TaskViewInvalidationAdapter` in the composition root instead of a legacy Signal
    subscription. Calling the handler directly proves the same busy-queueing property."""
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.tasksWorkspace
    controller._selected_project_id = "proj-1"
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    controller._set_is_busy(True)
    controller.onTaskListStale("proj-1")

    assert refresh_calls == []

    controller._set_is_busy(False)

    assert refresh_calls == ["refresh"]



def test_pm_collaboration_workspace_refreshes_on_collaboration_workflow_events(monkeypatch) -> None:
    """P44B: was `domain_events.collaboration_changed.emit(...)` (deleted -- durable Collaboration
    fully modernized onto typed DomainEvents + `TaskCommentViewInvalidationAdapter`, proved
    separately with real services in `test_p44b_collaboration_comment_full_modernization.py`).
    P45B: `tasks_changed` is also deleted -- Collaboration workspace's remaining Task dependency
    is now `onTaskProfileStale`, wired via a `TaskViewInvalidationAdapter` in the composition
    root (narrower than the old blanket subscription: only Task name/identity/existence facts,
    never progress/status/schedule/assignment/dependency)."""
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.collaborationWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    controller.onTaskProfileStale("proj-1")

    assert refresh_calls == ["refresh"]


def test_pm_portfolio_workspace_refreshes_on_portfolio_workflow_events(
    monkeypatch, qapp
) -> None:
    """P7A: direct-wired, no generic `domain_changed` bridge involved.

    P42: was `portfolio_changed`/`project_changed` -- `portfolio_changed` is deleted (Portfolio
    fully modernized onto typed DomainEvents + `PortfolioViewInvalidationAdapter`, proved
    separately with real services in `test_p42_portfolio_full_modernization.py`). P43: `project_
    changed` is also deleted (Project fully modernized onto typed DomainEvents +
    `ProjectViewInvalidationAdapter`, proved separately with real services in
    `test_p43_project_full_modernization.py`). P45B: `tasks_changed` is also deleted -- Portfolio's
    one remaining Task dependency (Executive/heatmap critical/late counts) is now `onTaskListStale`,
    wired via a `TaskViewInvalidationAdapter`, still using Portfolio's own debounced
    `_request_domain_refresh()` override to prove the same coalescing property."""
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.portfolioWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    controller.onTaskListStale("proj-1")
    QApplication.processEvents()

    assert refresh_calls == ["refresh"]


def test_platform_control_workspace_refreshes_on_control_events(monkeypatch) -> None:
    """P41-FIX precedent, extended by P45B: `tasks_changed` is deleted -- Platform Control's real
    dependency on PM's Task facts (approval-queue + audit-feed activity) is now delivered via
    `ProjectManagementWorkspaceCatalog.taskWorkspaceActivityStale`, connected in `app.py` to this
    same generic `onExternalViewStale` slot, with neither side importing the other's
    implementation. Calling the slot directly proves the property without needing the full
    cross-catalog wiring in this unit test."""
    catalog = PlatformWorkspaceCatalog()
    controller = catalog.controlWorkspace
    controller.ensureLoaded()
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    controller.onExternalViewStale("proj-1")

    assert refresh_calls == ["refresh"]


def test_platform_admin_access_workspace_reacts_to_account_security_change_narrowly(monkeypatch) -> None:
    """P46B: was `domain_events.auth_changed.emit(...)` -- Auth/Security is now fully modernized,
    so the access workspace reacts to the typed `account_security`/`authorization_context`
    ViewInvalidation targets instead, wired via `AccountSecurityViewInvalidationAdapter`/
    `AuthorizationContextViewInvalidationAdapter` in the composition root (`context.py`). Calling
    the handler directly proves the same narrow-reaction property, matching this file's own
    established pattern for every other capability above."""
    catalog = PlatformWorkspaceCatalog()
    controller = catalog.adminAccessWorkspace
    controller.ensureLoaded()
    narrow_calls: list[str] = []
    full_refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "_refresh_after_security_change", lambda: narrow_calls.append("security"))
    monkeypatch.setattr(controller, "refresh", lambda: full_refresh_calls.append("refresh"))

    controller.refresh_after_account_security_change()

    assert narrow_calls == ["security"]
    assert full_refresh_calls == []
