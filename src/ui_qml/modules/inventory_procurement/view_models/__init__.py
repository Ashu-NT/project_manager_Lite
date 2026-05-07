"""Inventory and procurement QML view models."""
from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryCatalogMetricViewModel,
    InventoryCatalogOverviewViewModel,
    InventoryCatalogWorkspaceViewModel,
    InventoryDetailFieldViewModel,
    InventoryDetailViewModel,
    InventoryDocumentOptionViewModel,
    InventoryRecordViewModel,
    InventorySelectorOptionViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.dashboard import (
    InventoryDashboardMetricViewModel,
    InventoryDashboardOverviewViewModel,
    InventoryDashboardRowViewModel,
    InventoryDashboardSectionViewModel,
    InventoryDashboardWorkspaceViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.inventory import (
    InventoryInventoryWorkspaceViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.pricing import (
    InventoryPricingWorkspaceViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.procurement import (
    InventoryProcurementProcurementWorkspaceViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.reservations import (
    InventoryReservationsWorkspaceViewModel,
)
from src.ui_qml.modules.inventory_procurement.view_models.workspace import (
    InventoryProcurementWorkspaceViewModel,
)

__all__ = [
    "InventoryCatalogMetricViewModel",
    "InventoryCatalogOverviewViewModel",
    "InventoryCatalogWorkspaceViewModel",
    "InventoryDashboardMetricViewModel",
    "InventoryDashboardOverviewViewModel",
    "InventoryDashboardRowViewModel",
    "InventoryDashboardSectionViewModel",
    "InventoryDashboardWorkspaceViewModel",
    "InventoryDetailFieldViewModel",
    "InventoryDetailViewModel",
    "InventoryDocumentOptionViewModel",
    "InventoryInventoryWorkspaceViewModel",
    "InventoryPricingWorkspaceViewModel",
    "InventoryProcurementProcurementWorkspaceViewModel",
    "InventoryProcurementWorkspaceViewModel",
    "InventoryRecordViewModel",
    "InventoryReservationsWorkspaceViewModel",
    "InventorySelectorOptionViewModel",
]
