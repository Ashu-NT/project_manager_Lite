"""Baseline management — creation, snapshots, variance, and comparison."""
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.scheduling.baselines.queries.comparison import (
    BaselineComparisonQueryHandler,
    BaselineComparisonReport,
    TaskVariance,
)

__all__ = [
    "BaselineComparisonReport",
    "BaselineComparisonQueryHandler",
    "BaselineService",
    "TaskVariance",
]
