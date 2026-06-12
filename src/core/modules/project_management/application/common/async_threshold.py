from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WorkloadScale(str, Enum):
    """Rough scale bucket used to select sync vs async execution path."""
    SMALL = "small"       # fits in a single interactive request
    MEDIUM = "medium"     # acceptable inline but consider background
    LARGE = "large"       # must run asynchronously
    XLARGE = "xlarge"     # always async, may need queue partitioning


@dataclass(frozen=True)
class AsyncThresholds:
    """
    Per-operation row-count thresholds that determine when a workload
    should move from inline synchronous execution to background/async.

    Defaults are calibrated for a typical PM desktop dataset.
    Pass custom thresholds at service construction time to tune per-deployment.
    """
    # CPM scheduling: number of tasks
    schedule_large: int = 500
    schedule_xlarge: int = 2000

    # Baseline comparison: number of baseline tasks
    baseline_compare_large: int = 1000
    baseline_compare_xlarge: int = 5000

    # Report generation: number of result rows
    report_large: int = 2000
    report_xlarge: int = 10000

    # Import parsing: number of source rows
    import_large: int = 500
    import_xlarge: int = 5000

    # Dashboard aggregation: number of projects in scope
    dashboard_large: int = 50
    dashboard_xlarge: int = 200

    # Portfolio resource pool: number of resources
    portfolio_large: int = 200
    portfolio_xlarge: int = 1000


#: Shared default instance — calibrated for a typical PM desktop dataset.
DEFAULT_ASYNC_THRESHOLDS = AsyncThresholds()


class AsyncThresholdGuard:
    """
    Evaluates whether a given workload should execute synchronously or be
    dispatched asynchronously, based on estimated row/entity counts.

    Services call should_run_async() before starting expensive computation.
    Application layers (API controllers, background workers) use the result
    to decide whether to run inline or enqueue.
    """

    def __init__(self, thresholds: AsyncThresholds | None = None) -> None:
        self._t: AsyncThresholds = thresholds if thresholds is not None else DEFAULT_ASYNC_THRESHOLDS

    def classify_schedule(self, task_count: int) -> WorkloadScale:
        if task_count >= self._t.schedule_xlarge:
            return WorkloadScale.XLARGE
        if task_count >= self._t.schedule_large:
            return WorkloadScale.LARGE
        if task_count >= self._t.schedule_large // 2:
            return WorkloadScale.MEDIUM
        return WorkloadScale.SMALL

    def classify_report(self, estimated_rows: int) -> WorkloadScale:
        if estimated_rows >= self._t.report_xlarge:
            return WorkloadScale.XLARGE
        if estimated_rows >= self._t.report_large:
            return WorkloadScale.LARGE
        if estimated_rows >= self._t.report_large // 2:
            return WorkloadScale.MEDIUM
        return WorkloadScale.SMALL

    def classify_import(self, source_row_count: int) -> WorkloadScale:
        if source_row_count >= self._t.import_xlarge:
            return WorkloadScale.XLARGE
        if source_row_count >= self._t.import_large:
            return WorkloadScale.LARGE
        if source_row_count >= self._t.import_large // 2:
            return WorkloadScale.MEDIUM
        return WorkloadScale.SMALL

    def classify_portfolio(self, resource_count: int) -> WorkloadScale:
        if resource_count >= self._t.portfolio_xlarge:
            return WorkloadScale.XLARGE
        if resource_count >= self._t.portfolio_large:
            return WorkloadScale.LARGE
        if resource_count >= self._t.portfolio_large // 2:
            return WorkloadScale.MEDIUM
        return WorkloadScale.SMALL

    def should_run_async(self, scale: WorkloadScale) -> bool:
        """Return True when the workload scale requires background execution."""
        return scale in (WorkloadScale.LARGE, WorkloadScale.XLARGE)


__all__ = ["AsyncThresholdGuard", "AsyncThresholds", "DEFAULT_ASYNC_THRESHOLDS", "WorkloadScale"]
