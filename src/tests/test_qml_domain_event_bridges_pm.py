from PySide6.QtWidgets import QApplication

from src.core.shared.events.domain_events import domain_events
from src.ui_qml.modules.project_management.context import (
    ProjectManagementWorkspaceCatalog,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


def test_pm_tasks_workspace_queues_domain_refresh_while_busy(monkeypatch) -> None:
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.tasksWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    controller._set_is_busy(True)
    domain_events.tasks_changed.emit("proj-1")
    domain_events.collaboration_changed.emit("task-1")

    assert refresh_calls == []

    controller._set_is_busy(False)

    assert refresh_calls == ["refresh"]



def test_pm_collaboration_workspace_refreshes_on_collaboration_workflow_events(monkeypatch) -> None:
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.collaborationWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.collaboration_changed.emit("task-1")

    assert refresh_calls == ["refresh"]


def test_pm_portfolio_workspace_refreshes_on_portfolio_workflow_events(
    monkeypatch, qapp
) -> None:
    """P7A: direct-wired -- `project_changed`/`tasks_changed` are the actual specific signals
    Portfolio's own debounced `_request_domain_refresh()` override coalesces into one refresh,
    no generic `domain_changed` bridge involved.

    P42: was `portfolio_changed`/`project_changed` -- `portfolio_changed` is deleted (Portfolio
    fully modernized onto typed DomainEvents + `PortfolioViewInvalidationAdapter`, proved
    separately with real services in `test_p42_portfolio_full_modernization.py`). This now uses
    `project_changed`/`tasks_changed`, Portfolio's two remaining legacy subscriptions, to keep
    proving the same coalescing property."""
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.portfolioWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.tasks_changed.emit("proj-1")
    domain_events.project_changed.emit("proj-1")
    QApplication.processEvents()

    assert refresh_calls == ["refresh"]


def test_platform_control_workspace_refreshes_on_control_events(monkeypatch) -> None:
    catalog = PlatformWorkspaceCatalog()
    controller = catalog.controlWorkspace
    controller.ensureLoaded()
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.tasks_changed.emit("proj-1")

    assert refresh_calls == ["refresh"]


def test_platform_admin_access_workspace_reacts_to_auth_changed_narrowly(monkeypatch) -> None:

    catalog = PlatformWorkspaceCatalog()
    controller = catalog.adminAccessWorkspace
    controller.ensureLoaded()
    narrow_calls: list[str] = []
    full_refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "_refresh_after_security_change", lambda: narrow_calls.append("security"))
    monkeypatch.setattr(controller, "refresh", lambda: full_refresh_calls.append("refresh"))

    domain_events.auth_changed.emit("user-1")

    assert narrow_calls == ["security"]
    assert full_refresh_calls == []
    assert not hasattr(domain_events, "access_changed")
