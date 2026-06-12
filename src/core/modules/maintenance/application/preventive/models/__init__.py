"""Preventive maintenance DTOs and result types."""

from src.core.modules.maintenance.application.preventive.models.candidates import (
    MaintenancePreventiveDueCandidate,
    MaintenanceTriggerEvaluation,
)
from src.core.modules.maintenance.application.preventive.models.results import (
    MaintenanceGeneratedWorkPackage,
    MaintenancePreventiveForecastRow,
    MaintenancePreventiveGenerationResult,
)

__all__ = [
    "MaintenanceGeneratedWorkPackage",
    "MaintenancePreventiveDueCandidate",
    "MaintenancePreventiveForecastRow",
    "MaintenancePreventiveGenerationResult",
    "MaintenanceTriggerEvaluation",
]
