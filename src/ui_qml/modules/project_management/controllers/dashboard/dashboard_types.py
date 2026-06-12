from __future__ import annotations

from typing import TypeAlias

DASHBOARD_CONTROLLER_LOGGER_NAME = (
    "src.ui_qml.modules.project_management.controllers.dashboard."
    "dashboard_workspace_controller"
)

DashboardMap: TypeAlias = dict[str, object]
DashboardObjectList: TypeAlias = list[dict[str, object]]
DashboardOptionList: TypeAlias = list[dict[str, str]]

def default_dashboard_overview(title: str) -> DashboardMap:
    return {
        "title": title or "Dashboard",
        "subtitle": "Select a project to see schedule and cost health.",
        "metrics": [],
    }

def default_activity_feed() -> DashboardMap:
    return {
        "title": "Recent Activity",
        "subtitle": "",
        "emptyState": "No recent activity is available yet.",
        "items": [],
    }

__all__ = [
    "DASHBOARD_CONTROLLER_LOGGER_NAME",
    "DashboardMap",
    "DashboardObjectList",
    "DashboardOptionList",
    "default_activity_feed",
    "default_dashboard_overview",
]
