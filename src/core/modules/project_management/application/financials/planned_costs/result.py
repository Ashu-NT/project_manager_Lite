from __future__ import annotations

from dataclasses import dataclass

from src.core.modules.project_management.domain.financials.planned_cost import (
    ProjectPlannedCostVersion,
    ResourceAllocationDiagnostic,
)


@dataclass(frozen=True, slots=True)
class PlannedCostCalculationResult:
    """Persisted version and transient calculation-time allocation diagnostics."""

    version: ProjectPlannedCostVersion
    diagnostics: tuple[ResourceAllocationDiagnostic, ...]


__all__ = ["PlannedCostCalculationResult"]
