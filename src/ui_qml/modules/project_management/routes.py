from __future__ import annotations

from pathlib import Path

from src.core.modules.project_management.api.desktop import (
    build_project_management_workspace_desktop_api,
)
from src.ui_qml.shell.routes import QmlRoute


_QML_FILE_BY_WORKSPACE_KEY: dict[str, str] = {
    "projects": "ProjectsWorkspace.qml",
    "tasks": "TasksWorkspace.qml",
    "scheduling": "SchedulingWorkspace.qml",
    "resources": "ResourcesWorkspace.qml",
    "financials": "FinancialsWorkspace.qml",
    "risk": "RiskWorkspace.qml",
    "portfolio": "PortfolioWorkspace.qml",
    "register": "RegisterWorkspace.qml",
    "collaboration": "CollaborationWorkspace.qml",
    "timesheets": "TimesheetsWorkspace.qml",
    "dashboard": "DashboardWorkspace.qml",
}


def project_management_qml_path(*parts: str) -> Path:
    return Path(__file__).resolve().parent / "qml" / Path(*parts)


def build_project_management_routes() -> list[QmlRoute]:
    desktop_api = build_project_management_workspace_desktop_api()
    return [
        QmlRoute(
            route_id=f"project_management.{descriptor.key}",
            module_code="project_management",
            module_label="Project Management",
            group_label="Workspaces",
            title=descriptor.title,
            qml_path=project_management_qml_path(
                "workspaces",
                descriptor.key,
                _QML_FILE_BY_WORKSPACE_KEY[descriptor.key],
            ),
            presenter_key=f"project_management.{descriptor.key}",
        )
        for descriptor in desktop_api.list_workspaces()
    ]


__all__ = ["build_project_management_routes", "project_management_qml_path"]
