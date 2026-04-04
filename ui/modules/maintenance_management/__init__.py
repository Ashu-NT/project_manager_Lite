"""User-interface package for the maintenance management module."""

from ui.modules.maintenance_management.assets import MaintenanceAssetsTab
from ui.modules.maintenance_management.dashboard import MaintenanceDashboardTab
from ui.modules.maintenance_management.reliability import MaintenanceReliabilityTab
from ui.modules.maintenance_management.requests import MaintenanceRequestsTab

__all__ = [
    "MaintenanceAssetsTab",
    "MaintenanceDashboardTab",
    "MaintenanceReliabilityTab",
    "MaintenanceRequestsTab",
]
