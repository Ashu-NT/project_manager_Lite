"""Compatibility wrapper for reporting data models."""

from core.services.reporting.models import (
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
