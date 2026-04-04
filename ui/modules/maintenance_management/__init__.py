"""User-interface package for the maintenance management module."""

from ui.modules.maintenance_management.dashboard import MaintenanceDashboardTab
from ui.modules.maintenance_management.reliability import MaintenanceReliabilityTab

__all__ = [
    "MaintenanceDashboardTab",
    "MaintenanceReliabilityTab",
]
