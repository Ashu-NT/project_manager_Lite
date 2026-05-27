"""Maintenance repository implementations."""

from src.core.modules.maintenance.infrastructure.persistence.repositories.preventive_instance_repository import (
    SqlAlchemyMaintenancePreventivePlanInstanceRepository,
)
from src.core.modules.maintenance.infrastructure.persistence.repositories.repository import (
    SqlAlchemyMaintenanceAssetComponentRepository,
    SqlAlchemyMaintenanceAssetRepository,
    SqlAlchemyMaintenanceIntegrationSourceRepository,
    SqlAlchemyMaintenanceLocationRepository,
    SqlAlchemyMaintenancePreventivePlanRepository,
    SqlAlchemyMaintenancePreventivePlanTaskRepository,
    SqlAlchemyMaintenanceSensorExceptionRepository,
    SqlAlchemyMaintenanceSensorReadingRepository,
    SqlAlchemyMaintenanceSensorRepository,
    SqlAlchemyMaintenanceSensorSourceMappingRepository,
    SqlAlchemyMaintenanceSystemRepository,
    SqlAlchemyMaintenanceTaskStepTemplateRepository,
    SqlAlchemyMaintenanceTaskTemplateRepository,
    SqlAlchemyMaintenanceWorkOrderMaterialRequirementRepository,
    SqlAlchemyMaintenanceWorkOrderRepository,
    SqlAlchemyMaintenanceWorkOrderTaskRepository,
    SqlAlchemyMaintenanceWorkOrderTaskStepRepository,
    SqlAlchemyMaintenanceWorkRequestRepository,
)
from src.core.modules.maintenance.infrastructure.persistence.repositories.reliability_repository import (
    SqlAlchemyMaintenanceDowntimeEventRepository,
    SqlAlchemyMaintenanceFailureCodeRepository,
)

__all__ = [
    "SqlAlchemyMaintenanceAssetComponentRepository",
    "SqlAlchemyMaintenanceAssetRepository",
    "SqlAlchemyMaintenanceDowntimeEventRepository",
    "SqlAlchemyMaintenanceFailureCodeRepository",
    "SqlAlchemyMaintenanceIntegrationSourceRepository",
    "SqlAlchemyMaintenanceLocationRepository",
    "SqlAlchemyMaintenancePreventivePlanInstanceRepository",
    "SqlAlchemyMaintenancePreventivePlanRepository",
    "SqlAlchemyMaintenancePreventivePlanTaskRepository",
    "SqlAlchemyMaintenanceSensorExceptionRepository",
    "SqlAlchemyMaintenanceSensorReadingRepository",
    "SqlAlchemyMaintenanceSensorRepository",
    "SqlAlchemyMaintenanceSensorSourceMappingRepository",
    "SqlAlchemyMaintenanceSystemRepository",
    "SqlAlchemyMaintenanceTaskStepTemplateRepository",
    "SqlAlchemyMaintenanceTaskTemplateRepository",
    "SqlAlchemyMaintenanceWorkOrderMaterialRequirementRepository",
    "SqlAlchemyMaintenanceWorkOrderRepository",
    "SqlAlchemyMaintenanceWorkOrderTaskRepository",
    "SqlAlchemyMaintenanceWorkOrderTaskStepRepository",
    "SqlAlchemyMaintenanceWorkRequestRepository",
]
