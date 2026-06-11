from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.workspace import (
    MaintenanceWorkspaceViewModel,
)


def serialize_workspace_view_model(
    view_model: MaintenanceWorkspaceViewModel,
) -> dict[str, str]:
    return {
        "routeId": view_model.route_id,
        "title": view_model.title,
        "summary": view_model.summary,
        "migrationStatus": view_model.migration_status,
        "legacyRuntimeStatus": view_model.legacy_runtime_status,
    }


__all__ = ["serialize_workspace_view_model"]
