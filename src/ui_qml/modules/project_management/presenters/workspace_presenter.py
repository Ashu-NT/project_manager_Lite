from __future__ import annotations

from src.ui_qml.modules.project_management.routes import build_project_management_routes
from src.ui_qml.modules.project_management.view_models.workspace import (
    ProjectManagementWorkspaceViewModel,
)


_WORKSPACE_SUMMARIES: dict[str, str] = {
    "project_management.projects": (
        "Project lifecycle, ownership, status, and project list workflows."
    ),
    "project_management.tasks": (
        "Task planning, progress, dependencies, assignments, and execution state."
    ),
    "project_management.scheduling": (
        "Calendars, baseline comparison, dependency graphs, and critical-path views."
    ),
    "project_management.resources": (
        "Resource capacity, allocation, project assignments, and utilization views."
    ),
    "project_management.financials": (
        "Project cost, labor, baseline budget, and financial reporting workflows."
    ),
    "project_management.risk": (
        "Project risk register, mitigation, severity, and review workflows."
    ),
    "project_management.portfolio": (
        "Portfolio summaries, cross-project visibility, and decision support."
    ),
    "project_management.register": (
        "Controlled project register records and governance-facing project history."
    ),
    "project_management.collaboration": (
        "Notes, shared discussions, import collaboration, and team coordination."
    ),
    "project_management.timesheets": (
        "Time entry, review, labor capture, and project time reporting."
    ),
    "project_management.dashboard": (
        "Project KPIs, health summaries, and executive delivery views."
    ),
}


class ProjectManagementWorkspacePresenter:
    def __init__(self, route_id: str) -> None:
        self._route_id = route_id

    def build_view_model(self) -> ProjectManagementWorkspaceViewModel:
        route_by_id = {route.route_id: route for route in build_project_management_routes()}
        route = route_by_id[self._route_id]
        return ProjectManagementWorkspaceViewModel(
            route_id=route.route_id,
            title=route.title,
            summary=_WORKSPACE_SUMMARIES[route.route_id],
            migration_status="QML landing zone ready",
            legacy_runtime_status="Existing QWidget screen remains active",
        )


def build_project_management_workspace_presenters() -> dict[
    str, ProjectManagementWorkspacePresenter
]:
    return {
        route.route_id: ProjectManagementWorkspacePresenter(route.route_id)
        for route in build_project_management_routes()
    }


__all__ = [
    "ProjectManagementWorkspacePresenter",
    "build_project_management_workspace_presenters",
]
