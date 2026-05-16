from __future__ import annotations

from pathlib import Path

from src.core.modules.maintenance.api.desktop import (
    build_maintenance_workspace_desktop_api,
)
from src.ui_qml.shell.routes import QmlRoute


_QML_FILE_BY_WORKSPACE_KEY: dict[str, str] = {
    "dashboard": "DashboardWorkspace.qml",
    "assets": "AssetsWorkspace.qml",
    "work_requests": "WorkRequestsWorkspace.qml",
    "work_orders": "WorkOrdersWorkspace.qml",
    "preventive": "PreventiveWorkspace.qml",
    "reliability": "ReliabilityWorkspace.qml",
    "planner": "PlannerWorkspace.qml",
}

_DISPLAY_TITLE_BY_WORKSPACE_KEY: dict[str, str] = {
    "dashboard": "Maintenance Dashboard",
}


def maintenance_qml_path(*parts: str) -> Path:
    return Path(__file__).resolve().parent / "qml" / Path(*parts)


def build_maintenance_routes() -> list[QmlRoute]:
    desktop_api = build_maintenance_workspace_desktop_api()
    return [
        QmlRoute(
            route_id=f"maintenance_management.{descriptor.key}",
            module_code="maintenance",
            module_label="Maintenance",
            group_label="Workspaces",
            title=_DISPLAY_TITLE_BY_WORKSPACE_KEY.get(descriptor.key, descriptor.title),
            qml_path=maintenance_qml_path(
                "workspaces",
                descriptor.key,
                _QML_FILE_BY_WORKSPACE_KEY[descriptor.key],
            ),
            presenter_key=f"maintenance_management.{descriptor.key}",
        )
        for descriptor in desktop_api.list_workspaces()
    ]


__all__ = ["build_maintenance_routes", "maintenance_qml_path"]
