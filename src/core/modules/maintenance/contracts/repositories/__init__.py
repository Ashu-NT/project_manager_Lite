"""Maintenance repository contracts."""

from src.core.modules.maintenance.contracts.repositories.assets import (
    MaintenanceAssetComponentRepository,
    MaintenanceAssetRepository,
    MaintenanceLocationRepository,
    MaintenanceSystemRepository,
)
from src.core.modules.maintenance.contracts.repositories.preventive import (
    MaintenanceBlackoutWindowRepository,
    MaintenancePreventivePlanInstanceRepository,
    MaintenancePreventivePlanRepository,
    MaintenancePreventivePlanTaskRepository,
    MaintenanceTaskStepTemplateRepository,
    MaintenanceTaskTemplateRepository,
)
from src.core.modules.maintenance.contracts.repositories.reliability import (
    MaintenanceDowntimeEventRepository,
    MaintenanceFailureCodeRepository,
    MaintenanceIntegrationSourceRepository,
    MaintenanceSensorExceptionRepository,
    MaintenanceSensorReadingRepository,
    MaintenanceSensorRepository,
    MaintenanceSensorSourceMappingRepository,
)
from src.core.modules.maintenance.contracts.repositories.work_orders import (
    MaintenanceWorkOrderMaterialRequirementRepository,
    MaintenanceWorkOrderRepository,
    MaintenanceWorkOrderTaskRepository,
    MaintenanceWorkOrderTaskStepRepository,
)
from src.core.modules.maintenance.contracts.repositories.work_requests import (
    MaintenanceWorkRequestRepository,
)

__all__ = [
    "MaintenanceBlackoutWindowRepository",
    "MaintenanceAssetComponentRepository",
    "MaintenanceAssetRepository",
    "MaintenanceDowntimeEventRepository",
    "MaintenanceFailureCodeRepository",
    "MaintenanceIntegrationSourceRepository",
    "MaintenanceLocationRepository",
    "MaintenancePreventivePlanInstanceRepository",
    "MaintenancePreventivePlanRepository",
    "MaintenancePreventivePlanTaskRepository",
    "MaintenanceSensorExceptionRepository",
    "MaintenanceSensorReadingRepository",
    "MaintenanceSensorRepository",
    "MaintenanceSensorSourceMappingRepository",
    "MaintenanceSystemRepository",
    "MaintenanceTaskStepTemplateRepository",
    "MaintenanceTaskTemplateRepository",
    "MaintenanceWorkOrderMaterialRequirementRepository",
    "MaintenanceWorkOrderRepository",
    "MaintenanceWorkOrderTaskRepository",
    "MaintenanceWorkOrderTaskStepRepository",
    "MaintenanceWorkRequestRepository",
]
