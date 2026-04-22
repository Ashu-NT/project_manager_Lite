from __future__ import annotations

from PySide6.QtCore import QObject, Slot

from src.ui_qml.modules.project_management.presenters import (
    ProjectDashboardPresenter,
    build_project_management_workspace_presenters,
)


class ProjectManagementWorkspaceCatalog(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._presenters = build_project_management_workspace_presenters()
        self._dashboard_presenter = ProjectDashboardPresenter()

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
        view_model = presenter.build_view_model()
        return {
            "routeId": view_model.route_id,
            "title": view_model.title,
            "summary": view_model.summary,
            "migrationStatus": view_model.migration_status,
            "legacyRuntimeStatus": view_model.legacy_runtime_status,
        }

    @Slot(result="QVariantMap")
    def dashboardOverview(self) -> dict[str, object]:
        view_model = self._dashboard_presenter.build_empty_overview()
        return {
            "title": view_model.title,
            "subtitle": view_model.subtitle,
            "metrics": [
                {
                    "label": metric.label,
                    "value": metric.value,
                    "supportingText": metric.supporting_text,
                }
                for metric in view_model.metrics
            ],
        }


__all__ = ["ProjectManagementWorkspaceCatalog"]
