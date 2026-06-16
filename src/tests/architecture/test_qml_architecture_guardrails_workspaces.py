from __future__ import annotations

from pathlib import Path

from src.tests.path_rewrites import REPO_ROOT

ROOT = REPO_ROOT
SRC_ROOT = ROOT / "src"
UI_QML_ROOT = SRC_ROOT / "ui_qml"
PLATFORM_ADMIN_CONSOLE_CONTROLLER = (
    UI_QML_ROOT / "platform" / "controllers" / "admin" / "admin_console_controller.py"
)
STALE_PLATFORM_ADMIN_WORKSPACE_CONTROLLER = (
    UI_QML_ROOT / "platform" / "controllers" / "admin" / "admin_workspace_controller.py"
)


def test_platform_admin_workspace_controller_uses_split_entrypoint() -> None:
    assert PLATFORM_ADMIN_CONSOLE_CONTROLLER.exists()
    assert not STALE_PLATFORM_ADMIN_WORKSPACE_CONTROLLER.exists()


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


def test_project_management_risk_workspace_no_longer_uses_placeholder_page() -> None:
    risk_workspace = (
        UI_QML_ROOT
        / "modules"
        / "project_management"
        / "qml"
        / "workspaces"
        / "risk"
        / "RiskWorkspace.qml"
    )
    text = risk_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "RiskWorkspacePage" in text
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


def test_maintenance_dashboard_workspace_no_longer_uses_placeholder_page() -> None:
    dashboard_workspace = (
        UI_QML_ROOT
        / "modules"
        / "maintenance"
        / "qml"
        / "workspaces"
        / "dashboard"
        / "DashboardWorkspace.qml"
    )
    text = dashboard_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "DashboardWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_maintenance_assets_workspace_no_longer_uses_placeholder_page() -> None:
    assets_workspace = (
        UI_QML_ROOT
        / "modules"
        / "maintenance"
        / "qml"
        / "workspaces"
        / "assets"
        / "AssetsWorkspace.qml"
    )
    text = assets_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "AssetsWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_maintenance_reliability_workspace_no_longer_uses_placeholder_page() -> None:
    reliability_workspace = (
        UI_QML_ROOT
        / "modules"
        / "maintenance"
        / "qml"
        / "workspaces"
        / "reliability"
        / "ReliabilityWorkspace.qml"
    )
    text = reliability_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "ReliabilityWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_maintenance_planner_workspace_no_longer_uses_placeholder_page() -> None:
    planner_workspace = (
        UI_QML_ROOT
        / "modules"
        / "maintenance"
        / "qml"
        / "workspaces"
        / "planner"
        / "PlannerWorkspace.qml"
    )
    text = planner_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "PlannerWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_maintenance_work_requests_workspace_no_longer_uses_placeholder_page() -> None:
    work_requests_workspace = (
        UI_QML_ROOT
        / "modules"
        / "maintenance"
        / "qml"
        / "workspaces"
        / "work_requests"
        / "WorkRequestsWorkspace.qml"
    )
    text = work_requests_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "WorkRequestsWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_maintenance_work_orders_workspace_no_longer_uses_placeholder_page() -> None:
    work_orders_workspace = (
        UI_QML_ROOT
        / "modules"
        / "maintenance"
        / "qml"
        / "workspaces"
        / "work_orders"
        / "WorkOrdersWorkspace.qml"
    )
    text = work_orders_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "WorkOrdersWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text


def test_maintenance_preventive_workspace_no_longer_uses_placeholder_page() -> None:
    preventive_workspace = (
        UI_QML_ROOT
        / "modules"
        / "maintenance"
        / "qml"
        / "workspaces"
        / "preventive"
        / "PreventiveWorkspace.qml"
    )
    text = preventive_workspace.read_text(encoding="utf-8", errors="ignore")

    assert "PreventiveWorkspacePage" in text
    assert "WorkspacePlaceholderPage" not in text
