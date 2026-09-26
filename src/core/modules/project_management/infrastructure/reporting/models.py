"""Backward-compat shim — implementations live in models/report_models.py."""

from src.core.modules.project_management.application.dashboard.models.report_models import (
    BaselineComparisonResult,
    BaselineComparisonRow,
    CostBreakdownRow,
    CostSourceBreakdown,
    CostSourceRow,
    EarnedValueMetrics,
    EvmSeriesPoint,
    GanttTaskBar,
    LaborAssignmentRow,
    LaborResourceRow,
    ProjectKPI,
    ResourceLoadRow,
    TaskVarianceRow,
)

__all__ = [
    "BaselineComparisonResult",
    "BaselineComparisonRow",
    "CostBreakdownRow",
    "CostSourceBreakdown",
    "CostSourceRow",
    "EarnedValueMetrics",
    "EvmSeriesPoint",
    "GanttTaskBar",
    "LaborAssignmentRow",
    "LaborResourceRow",
    "ProjectKPI",
    "ResourceLoadRow",
    "TaskVarianceRow",
]
