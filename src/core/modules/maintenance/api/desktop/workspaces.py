from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MaintenanceWorkspaceDescriptor:
    key: str
    title: str
    summary: str


_WORKSPACE_DESCRIPTORS: tuple[MaintenanceWorkspaceDescriptor, ...] = (
    MaintenanceWorkspaceDescriptor(
        key="dashboard",
        title="Dashboard",
        summary="Reliability KPIs, execution backlog, compliance watchlists, and downtime health.",
    ),
    MaintenanceWorkspaceDescriptor(
        key="assets",
        title="Assets",
        summary="Sites, locations, systems, assets, and component-library structures for maintenance scope.",
    ),
    MaintenanceWorkspaceDescriptor(
        key="work_requests",
        title="Work Requests",
        summary="Request intake, triage, conversion to execution, and backlog prioritization.",
    ),
    MaintenanceWorkspaceDescriptor(
        key="work_orders",
        title="Work Orders",
        summary="Execution planning, task/step tracking, labor, materials, and evidence capture.",
    ),
    MaintenanceWorkspaceDescriptor(
        key="preventive",
        title="Preventive",
        summary="Plans, task templates, generated work packages, and schedule compliance management.",
    ),
    MaintenanceWorkspaceDescriptor(
        key="reliability",
        title="Reliability",
        summary="Sensors, readings, exceptions, downtime events, and recurring-failure analysis.",
    ),
    MaintenanceWorkspaceDescriptor(
        key="planner",
        title="Planner",
        summary="Forward maintenance scheduling, release readiness, and capacity-aware planning views.",
    ),
)


class MaintenanceWorkspaceDesktopApi:
    def __init__(
        self,
        descriptors: tuple[MaintenanceWorkspaceDescriptor, ...] = _WORKSPACE_DESCRIPTORS,
    ) -> None:
        self._descriptors = descriptors
        self._descriptor_by_route_id = {
            f"maintenance_management.{descriptor.key}": descriptor
            for descriptor in descriptors
        }

    def list_workspaces(self) -> list[MaintenanceWorkspaceDescriptor]:
        return list(self._descriptors)

    def get_workspace(self, route_id: str) -> MaintenanceWorkspaceDescriptor | None:
        return self._descriptor_by_route_id.get(route_id)


def build_maintenance_workspace_desktop_api() -> MaintenanceWorkspaceDesktopApi:
    return MaintenanceWorkspaceDesktopApi()


__all__ = [
    "MaintenanceWorkspaceDescriptor",
    "MaintenanceWorkspaceDesktopApi",
    "build_maintenance_workspace_desktop_api",
]
