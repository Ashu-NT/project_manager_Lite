from __future__ import annotations

from PySide6.QtQml import qmlRegisterModule, qmlRegisterUncreatableType

from src.ui_qml.modules.inventory_procurement.context import (
    InventoryProcurementWorkspaceCatalog,
)
from src.ui_qml.modules.inventory_procurement.controllers import (
    InventoryProcurementCatalogWorkspaceController,
    InventoryProcurementDashboardWorkspaceController,
    InventoryProcurementWorkspaceControllerBase,
)

_REGISTERED = False


def register_inventory_procurement_qml_types() -> None:
    global _REGISTERED
    if _REGISTERED:
        return

    qmlRegisterModule("InventoryProcurement.Controllers", 1, 0)
    qmlRegisterUncreatableType(
        InventoryProcurementWorkspaceControllerBase,
        "InventoryProcurement.Controllers",
        1,
        0,
        "InventoryProcurementWorkspaceControllerBase",
        "Inventory workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        InventoryProcurementCatalogWorkspaceController,
        "InventoryProcurement.Controllers",
        1,
        0,
        "InventoryProcurementCatalogWorkspaceController",
        "Inventory workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        InventoryProcurementDashboardWorkspaceController,
        "InventoryProcurement.Controllers",
        1,
        0,
        "InventoryProcurementDashboardWorkspaceController",
        "Inventory workspace controllers are provided by the shell runtime.",
    )
    qmlRegisterUncreatableType(
        InventoryProcurementWorkspaceCatalog,
        "InventoryProcurement.Controllers",
        1,
        0,
        "InventoryProcurementWorkspaceCatalog",
        "Inventory workspace catalogs are provided by the shell runtime.",
    )
    _REGISTERED = True


__all__ = ["register_inventory_procurement_qml_types"]
