"""User-interface package for the maintenance management module."""

from ui.modules.maintenance_management.asset_library import MaintenanceAssetLibraryTab
from ui.modules.maintenance_management.assets import MaintenanceAssetsTab
from ui.modules.maintenance_management.dashboard import MaintenanceDashboardTab
from ui.modules.maintenance_management.documents import MaintenanceDocumentsTab
from ui.modules.maintenance_management.locations import MaintenanceLocationsTab
from ui.modules.maintenance_management.planner import MaintenancePlannerTab
from ui.modules.maintenance_management.preventive_library import MaintenancePreventivePlanLibraryTab
from ui.modules.maintenance_management.preventive import MaintenancePreventivePlansTab
from ui.modules.maintenance_management.reliability import MaintenanceReliabilityTab
from ui.modules.maintenance_management.requests import MaintenanceRequestsTab
from ui.modules.maintenance_management.sensors import MaintenanceSensorsTab
from ui.modules.maintenance_management.systems import MaintenanceSystemsTab
from ui.modules.maintenance_management.task_templates import MaintenanceTaskTemplatesTab
from ui.modules.maintenance_management.work_orders import MaintenanceWorkOrdersTab

__all__ = [
    "MaintenanceAssetLibraryTab",
    "MaintenanceAssetsTab",
    "MaintenanceDashboardTab",
    "MaintenanceDocumentsTab",
    "MaintenanceLocationsTab",
    "MaintenancePlannerTab",
    "MaintenancePreventivePlanLibraryTab",
    "MaintenancePreventivePlansTab",
    "MaintenanceReliabilityTab",
    "MaintenanceRequestsTab",
    "MaintenanceSensorsTab",
    "MaintenanceSystemsTab",
    "MaintenanceTaskTemplatesTab",
    "MaintenanceWorkOrdersTab",
]
