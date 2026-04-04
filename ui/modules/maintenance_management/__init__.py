"""User-interface package for the maintenance management module."""

from ui.modules.maintenance_management.assets import MaintenanceAssetsTab
from ui.modules.maintenance_management.dashboard import MaintenanceDashboardTab
from ui.modules.maintenance_management.documents import MaintenanceDocumentsTab
from ui.modules.maintenance_management.reliability import MaintenanceReliabilityTab
from ui.modules.maintenance_management.requests import MaintenanceRequestsTab
from ui.modules.maintenance_management.sensors import MaintenanceSensorsTab
from ui.modules.maintenance_management.work_orders import MaintenanceWorkOrdersTab

__all__ = [
    "MaintenanceAssetsTab",
    "MaintenanceDashboardTab",
    "MaintenanceDocumentsTab",
    "MaintenanceReliabilityTab",
    "MaintenanceRequestsTab",
    "MaintenanceSensorsTab",
    "MaintenanceWorkOrdersTab",
]
