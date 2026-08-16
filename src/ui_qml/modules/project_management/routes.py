from __future__ import annotations

from pathlib import Path

from src.core.modules.project_management.api.desktop import (
    build_project_management_workspace_desktop_api,
)
from src.ui_qml.modules.project_management.navigation import PM_CANONICAL_ROUTE_ID
from src.ui_qml.shell.routes import QmlRoute


# R2.8: each of the ten route ids' qml_path now points at a small bridge
# component (qml/workspace/compatibility/) that loads the SAME canonical
# shell as the PM_CANONICAL_ROUTE_ID route below and applies this route's
# destination through navigation.py's single authoritative
# compatibility_route_intent()/applyRoute() mapping. "Compatibility route"
# is the term the approved target design/restructure plan docs already use
# ("migration and deep-link compatibility routes") -- there is no installed
# client base, so this isn't about preserving an external contract, only
# the internal deep-link shape while callers/tests migrate to the canonical
# route. This is a behavior CHANGE from the pre-R2 baseline (these routes
# used to load the bare capability page directly, with no shell chrome) --
# the ten route ids themselves, and every capability page's own
# file/content, are unchanged.
_COMPATIBILITY_BRIDGE_FILE_BY_WORKSPACE_KEY: dict[str, str] = {
    "projects": "ProjectsRoute.qml",
    "tasks": "TasksRoute.qml",
    "scheduling": "SchedulingRoute.qml",
    "resources": "ResourcesRoute.qml",
    "financials": "FinancialsRoute.qml",
    "portfolio": "PortfolioRoute.qml",
    "register": "RegisterRoute.qml",
    "collaboration": "CollaborationRoute.qml",
    "timesheets": "TimesheetsRoute.qml",
    "dashboard": "DashboardRoute.qml",
}


def project_management_qml_path(*parts: str) -> Path:
    return Path(__file__).resolve().parent / "qml" / Path(*parts)


def build_project_management_routes() -> list[QmlRoute]:
    desktop_api = build_project_management_workspace_desktop_api()
    canonical_route = QmlRoute(
        route_id=PM_CANONICAL_ROUTE_ID,
        module_code="project_management",
        module_label="Project Management",
        group_label="Workspaces",
        title="Project Management",
        qml_path=project_management_qml_path("workspace", "ProjectManagementWorkspace.qml"),
        presenter_key=None,
        appears_in_navigation=True,
    )
    compatibility_routes = [
        QmlRoute(
            route_id=f"project_management.{descriptor.key}",
            module_code="project_management",
            module_label="Project Management",
            group_label="Workspaces",
            title=descriptor.title,
            qml_path=project_management_qml_path(
                "workspace",
                "compatibility",
                _COMPATIBILITY_BRIDGE_FILE_BY_WORKSPACE_KEY[descriptor.key],
            ),
            presenter_key=f"project_management.{descriptor.key}",
            appears_in_navigation=False,
        )
        for descriptor in desktop_api.list_workspaces()
    ]
    return [canonical_route, *compatibility_routes]


__all__ = ["build_project_management_routes", "project_management_qml_path"]
