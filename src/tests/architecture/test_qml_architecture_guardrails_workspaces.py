from __future__ import annotations

from pathlib import Path

from src.tests.path_rewrites import REPO_ROOT

ROOT = REPO_ROOT
SRC_ROOT = ROOT / "src"
UI_QML_ROOT = SRC_ROOT / "ui_qml"
PLATFORM_ADMIN_CONSOLE_CONTROLLER = (
    UI_QML_ROOT / "platform" / "controllers" / "admin_console" / "admin_console_controller.py"
)
STALE_PLATFORM_ADMIN_DIRECTORY = UI_QML_ROOT / "platform" / "controllers" / "admin"
STALE_PLATFORM_ADMIN_WORKSPACE_CONTROLLER = (
    UI_QML_ROOT / "platform" / "controllers" / "admin_console" / "admin_workspace_controller.py"
)


def test_platform_admin_workspace_controller_uses_split_entrypoint() -> None:
    assert PLATFORM_ADMIN_CONSOLE_CONTROLLER.exists()
    assert not STALE_PLATFORM_ADMIN_WORKSPACE_CONTROLLER.exists()
    assert not STALE_PLATFORM_ADMIN_DIRECTORY.exists()


def test_project_management_projects_workspace_no_longer_uses_placeholder_page() -> None:
    projects_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "projects"
        / "ProjectsWorkspace.qml"
    )
    text = projects_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "ProjectsWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_tasks_workspace_no_longer_uses_placeholder_page() -> None:
    tasks_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "tasks"
        / "TasksWorkspace.qml"
    )
    text = tasks_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "TasksWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_scheduling_workspace_no_longer_uses_placeholder_page() -> None:
    scheduling_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "scheduling"
        / "SchedulingWorkspace.qml"
    )
    text = scheduling_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "SchedulingWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_resources_workspace_no_longer_uses_placeholder_page() -> None:
    resources_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "resources"
        / "ResourcesWorkspace.qml"
    )
    text = resources_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "ResourcesWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_financials_workspace_no_longer_uses_placeholder_page() -> None:
    financials_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "financials"
        / "FinancialsWorkspace.qml"
    )
    text = financials_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "FinancialsWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_register_workspace_no_longer_uses_placeholder_page() -> None:
    register_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "register"
        / "RegisterWorkspace.qml"
    )
    text = register_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "RegisterWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_collaboration_workspace_no_longer_uses_placeholder_page() -> None:
    collaboration_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "collaboration"
        / "CollaborationWorkspace.qml"
    )
    text = collaboration_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "CollaborationWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_portfolio_workspace_no_longer_uses_placeholder_page() -> None:
    portfolio_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "portfolio"
        / "PortfolioWorkspace.qml"
    )
    text = portfolio_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "PortfolioWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_project_management_timesheets_workspace_no_longer_uses_placeholder_page() -> None:
    timesheets_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "timesheets"
        / "TimesheetsWorkspace.qml"
    )
    text = timesheets_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "TimesheetsWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_inventory_pricing_workspace_no_longer_uses_placeholder_page() -> None:
    pricing_workspace = (
        UI_QML_ROOT
        / "modules"
        / "inventory_procurement"
        / "qml"
        / "workspaces"
        / "pricing"
        / "PricingWorkspace.qml"
    )
    text = pricing_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "PricingWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


