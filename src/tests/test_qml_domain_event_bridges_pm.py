from PySide6.QtWidgets import QApplication

from src.core.shared.events.domain_events import DomainChangeEvent, domain_events
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
    domain_events.timesheet_periods_changed.emit("period-1")

    assert refresh_calls == []

    controller._set_is_busy(False)

    assert refresh_calls == ["refresh"]


def test_pm_resources_workspace_refreshes_on_resource_and_employee_events(monkeypatch) -> None:
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.resourcesWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.resources_changed.emit("res-1")
    domain_events.employees_changed.emit("emp-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_pm_collaboration_workspace_refreshes_on_collaboration_workflow_events(monkeypatch) -> None:
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.collaborationWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.collaboration_changed.emit("task-1")
    domain_events.approvals_changed.emit("approval-1")
    domain_events.timesheet_periods_changed.emit("period-1")

    assert refresh_calls == ["refresh", "refresh", "refresh"]


def test_pm_portfolio_workspace_refreshes_on_portfolio_workflow_events(
    monkeypatch, qapp
) -> None:
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.portfolioWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.domain_changed.emit(
        DomainChangeEvent(
            category="module",
            scope_code="project_management",
            entity_type="portfolio_entity",
            entity_id="portfolio-1",
            source_event="manual_test",
        )
    )
    domain_events.domain_changed.emit(
        DomainChangeEvent(
            category="module",
            scope_code="project_management",
            entity_type="project",
            entity_id="proj-1",
            source_event="manual_test",
        )
    )
    QApplication.processEvents()

    assert refresh_calls == ["refresh"]


def test_pm_timesheets_workspace_refreshes_on_timesheet_workflow_events(monkeypatch) -> None:
    catalog = ProjectManagementWorkspaceCatalog()
    controller = catalog.timesheetsWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.timesheet_periods_changed.emit("period-1")
    domain_events.resources_changed.emit("res-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_platform_control_workspace_refreshes_on_control_events(monkeypatch) -> None:
    catalog = PlatformWorkspaceCatalog()
    controller = catalog.controlWorkspace
    controller.ensureLoaded()
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.approvals_changed.emit("approval-1")
    domain_events.costs_changed.emit("proj-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_platform_settings_workspace_refreshes_on_runtime_events(monkeypatch) -> None:
    catalog = PlatformWorkspaceCatalog()
    controller = catalog.settingsWorkspace
    controller.ensureLoaded()
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.modules_changed.emit("project_management")
    domain_events.organizations_changed.emit("org-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_platform_admin_access_workspace_refreshes_on_access_events(monkeypatch) -> None:
    catalog = PlatformWorkspaceCatalog()
    controller = catalog.adminAccessWorkspace
    controller.ensureLoaded()
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.auth_changed.emit("user-1")
    domain_events.access_changed.emit("project-1")

    assert refresh_calls == ["refresh", "refresh"]


def test_platform_admin_workspace_refreshes_on_master_data_events(monkeypatch) -> None:
    catalog = PlatformWorkspaceCatalog()
    controller = catalog.adminWorkspace
    refresh_calls: list[str] = []
    monkeypatch.setattr(controller, "refresh", lambda: refresh_calls.append("refresh"))

    domain_events.organizations_changed.emit("org-1")
    domain_events.documents_changed.emit("doc-1")

    assert refresh_calls == ["refresh", "refresh"]
