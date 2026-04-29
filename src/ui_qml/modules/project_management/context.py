from __future__ import annotations

from PySide6.QtCore import Property, QObject, Slot

from src.ui_qml.modules.project_management.controllers import (
    ProjectManagementDashboardWorkspaceController,
)
from src.ui_qml.modules.project_management.controllers.common import (
    serialize_workspace_view_model,
)
from src.ui_qml.modules.project_management.presenters import (
    build_project_management_workspace_presenters,
)


class ProjectManagementWorkspaceCatalog(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._presenters = build_project_management_workspace_presenters()
        self._dashboard_workspace = ProjectManagementDashboardWorkspaceController(
            parent=self
        )

    @Property(ProjectManagementDashboardWorkspaceController, constant=True)
    def dashboardWorkspace(self) -> ProjectManagementDashboardWorkspaceController:
        return self._dashboard_workspace

    @Slot(str, result="QVariantMap")
    def workspace(self, route_id: str) -> dict[str, str]:
        presenter = self._presenters.get(route_id)
        if presenter is None:
            return {
                "routeId": route_id,
                "title": "",
                "summary": "",
                "migrationStatus": "",
                "legacyRuntimeStatus": "",
            }
        return serialize_workspace_view_model(presenter.build_view_model())

    @Slot(result="QVariantMap")
    def dashboardOverview(self) -> dict[str, object]:
        return dict(self._dashboard_workspace.overview)


__all__ = ["ProjectManagementWorkspaceCatalog"]
