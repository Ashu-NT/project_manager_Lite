"""Compatibility wrapper for ReportingService and related model exports."""

from core.services.reporting.service import ReportingService
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
from core.services.scheduling.engine import CPMTaskInfo

__all__ = [
    "ReportingService",
    "CPMTaskInfo",
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
