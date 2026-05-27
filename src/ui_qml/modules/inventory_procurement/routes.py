from __future__ import annotations

from pathlib import Path

from src.core.modules.inventory_procurement.api.desktop import (
    build_inventory_procurement_workspace_desktop_api,
)
from src.ui_qml.shell.routes import QmlRoute


_QML_FILE_BY_WORKSPACE_KEY: dict[str, str] = {
    "dashboard": "DashboardWorkspace.qml",
    "catalog": "CatalogWorkspace.qml",
    "inventory": "InventoryWorkspace.qml",
    "reservations": "ReservationsWorkspace.qml",
    "procurement": "ProcurementWorkspace.qml",
    "pricing": "PricingWorkspace.qml",
    "movements": "StockMovementsWorkspace.qml",
}

_DISPLAY_TITLE_BY_WORKSPACE_KEY: dict[str, str] = {
    "dashboard": "Inventory Dashboard",
}


def inventory_procurement_qml_path(*parts: str) -> Path:
    return Path(__file__).resolve().parent / "qml" / Path(*parts)


def build_inventory_procurement_routes() -> list[QmlRoute]:
    desktop_api = build_inventory_procurement_workspace_desktop_api()
    return [
        QmlRoute(
            route_id=f"inventory_procurement.{descriptor.key}",
            module_code="inventory_procurement",
            module_label="Inventory & Procurement",
            group_label="Workspaces",
            title=_DISPLAY_TITLE_BY_WORKSPACE_KEY.get(descriptor.key, descriptor.title),
            qml_path=inventory_procurement_qml_path(
                "workspaces",
                descriptor.key,
                _QML_FILE_BY_WORKSPACE_KEY[descriptor.key],
            ),
            presenter_key=f"inventory_procurement.{descriptor.key}",
        )
        for descriptor in desktop_api.list_workspaces()
    ]


__all__ = ["build_inventory_procurement_routes", "inventory_procurement_qml_path"]
