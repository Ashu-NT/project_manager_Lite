from __future__ import annotations

from pathlib import Path

from src.ui_qml.shell.routes import QmlRoute


_WORKSPACE_ROUTES: tuple[tuple[str, str, str], ...] = (
    ("projects", "Projects", "ProjectsWorkspace.qml"),
    ("tasks", "Tasks", "TasksWorkspace.qml"),
    ("scheduling", "Scheduling", "SchedulingWorkspace.qml"),
    ("resources", "Resources", "ResourcesWorkspace.qml"),
    ("financials", "Financials", "FinancialsWorkspace.qml"),
    ("risk", "Risk", "RiskWorkspace.qml"),
    ("portfolio", "Portfolio", "PortfolioWorkspace.qml"),
    ("register", "Register", "RegisterWorkspace.qml"),
    ("collaboration", "Collaboration", "CollaborationWorkspace.qml"),
    ("timesheets", "Timesheets", "TimesheetsWorkspace.qml"),
    ("dashboard", "Dashboard", "DashboardWorkspace.qml"),
)


def project_management_qml_path(*parts: str) -> Path:
    return Path(__file__).resolve().parent / "qml" / Path(*parts)


def build_project_management_routes() -> list[QmlRoute]:
    return [
        QmlRoute(
            route_id=f"project_management.{workspace}",
            module_code="project_management",
            module_label="Project Management",
            group_label="Workspaces",
            title=title,
            qml_path=project_management_qml_path(
                "workspaces", workspace, qml_file
            ),
            presenter_key=f"project_management.{workspace}",
        )
        for workspace, title, qml_file in _WORKSPACE_ROUTES
    ]


__all__ = ["build_project_management_routes", "project_management_qml_path"]
