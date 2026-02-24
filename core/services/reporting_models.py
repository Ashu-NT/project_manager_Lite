"""Compatibility wrapper for reporting data models."""

from core.services.reporting.models import (
    BaselineComparisonResult,
    BaselineComparisonRow,
    EvmSeriesPoint,
    EarnedValueMetrics,
    LaborAssignmentRow,
    LaborResourceRow,
    LaborPlanActualRow,
    GanttTaskBar,
    ProjectKPI,
    ResourceLoadRow,
    TaskVarianceRow,
    CostBreakdownRow,
)

__all__ = [
    "BaselineComparisonResult",
    "BaselineComparisonRow",
    "EvmSeriesPoint",
    "EarnedValueMetrics",
    "LaborAssignmentRow",
    "LaborResourceRow",
    "LaborPlanActualRow",
    "GanttTaskBar",
    "ProjectKPI",
    "ResourceLoadRow",
    "TaskVarianceRow",
    "CostBreakdownRow",
]
