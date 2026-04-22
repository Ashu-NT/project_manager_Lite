from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectManagementWorkspaceDescriptor:
    key: str
    title: str
    summary: str


_WORKSPACE_DESCRIPTORS: tuple[ProjectManagementWorkspaceDescriptor, ...] = (
    ProjectManagementWorkspaceDescriptor(
        key="projects",
        title="Projects",
        summary="Project lifecycle, ownership, status, and project list workflows.",
    ),
    ProjectManagementWorkspaceDescriptor(
        key="tasks",
        title="Tasks",
        summary="Task planning, progress, dependencies, assignments, and execution state.",
    ),
    ProjectManagementWorkspaceDescriptor(
        key="scheduling",
        title="Scheduling",
        summary="Calendars, baseline comparison, dependency graphs, and critical-path views.",
    ),
    ProjectManagementWorkspaceDescriptor(
        key="resources",
        title="Resources",
        summary="Resource capacity, allocation, project assignments, and utilization views.",
    ),
    ProjectManagementWorkspaceDescriptor(
        key="financials",
        title="Financials",
        summary="Project cost, labor, baseline budget, and financial reporting workflows.",
    ),
    ProjectManagementWorkspaceDescriptor(
        key="risk",
        title="Risk",
        summary="Project risk register, mitigation, severity, and review workflows.",
    ),
    ProjectManagementWorkspaceDescriptor(
        key="portfolio",
        title="Portfolio",
        summary="Portfolio summaries, cross-project visibility, and decision support.",
    ),
    ProjectManagementWorkspaceDescriptor(
        key="register",
        title="Register",
        summary="Controlled project register records and governance-facing project history.",
    ),
    ProjectManagementWorkspaceDescriptor(
        key="collaboration",
        title="Collaboration",
        summary="Notes, shared discussions, import collaboration, and team coordination.",
    ),
    ProjectManagementWorkspaceDescriptor(
        key="timesheets",
        title="Timesheets",
        summary="Time entry, review, labor capture, and project time reporting.",
    ),
    ProjectManagementWorkspaceDescriptor(
        key="dashboard",
        title="Dashboard",
        summary="Project KPIs, health summaries, and executive delivery views.",
    ),
)


class ProjectManagementWorkspaceDesktopApi:
    def __init__(
        self,
        descriptors: tuple[
            ProjectManagementWorkspaceDescriptor, ...
        ] = _WORKSPACE_DESCRIPTORS,
    ) -> None:
        self._descriptors = descriptors
        self._descriptor_by_route_id = {
            f"project_management.{descriptor.key}": descriptor
            for descriptor in descriptors
        }

    def list_workspaces(self) -> list[ProjectManagementWorkspaceDescriptor]:
        return list(self._descriptors)

    def get_workspace(
        self, route_id: str
    ) -> ProjectManagementWorkspaceDescriptor | None:
        return self._descriptor_by_route_id.get(route_id)


def build_project_management_workspace_desktop_api() -> (
    ProjectManagementWorkspaceDesktopApi
):
    return ProjectManagementWorkspaceDesktopApi()


__all__ = [
    "ProjectManagementWorkspaceDescriptor",
    "ProjectManagementWorkspaceDesktopApi",
    "build_project_management_workspace_desktop_api",
]
