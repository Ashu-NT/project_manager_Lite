from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.workspace import (
    InventoryProcurementWorkspaceViewModel,
)


def serialize_workspace_view_model(
    view_model: InventoryProcurementWorkspaceViewModel,
) -> dict[str, str]:
    return {
        "routeId": view_model.route_id,
        "title": view_model.title,
        "summary": view_model.summary,
        "migrationStatus": view_model.migration_status,
        "legacyRuntimeStatus": view_model.legacy_runtime_status,
    }
