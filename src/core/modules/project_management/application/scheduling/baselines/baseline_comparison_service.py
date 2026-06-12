from __future__ import annotations

from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.contracts.repositories.baseline import BaselineRepository
from src.core.modules.project_management.domain.scheduling.baseline import BaselineTask, ProjectBaseline
from src.core.modules.project_management.application.scheduling.models.cpm import CPMTaskInfo
from src.core.platform.common.exceptions import NotFoundError


@dataclass
class TaskVariance:
    task_id: str
    task_name: str
    baseline_start: date | None
    baseline_finish: date | None
    current_start: date | None
    current_finish: date | None
    start_variance_days: int | None     # positive = delayed, negative = early
    finish_variance_days: int | None
    duration_variance_days: int | None
    cost_variance: float | None         # current_cost - baseline_cost
    is_delayed: bool
    is_critical: bool


@dataclass
class BaselineComparisonReport:
    baseline_id: str
    baseline_name: str
    project_id: str
    compared_at: date
    task_variances: list[TaskVariance]
    total_schedule_slippage_days: int      # max finish variance across all tasks
    tasks_delayed: int
    tasks_on_time: int
    tasks_early: int
    total_cost_variance: float


class BaselineComparisonService:
    """
    Compares the current computed CPM schedule against a stored project baseline
    and produces a variance report.

    The BaselineService owns creation/lifecycle of baselines.
    This service owns comparison and variance calculation.
    """

    def __init__(
        self,
        baseline_repo: BaselineRepository,
        calendar: CalendarProtocol,
    ) -> None:
        self._baselines = baseline_repo
        self._calendar = calendar

    def compare(
        self,
        project_id: str,
        cpm_result: dict[str, CPMTaskInfo],
        baseline_id: str | None = None,
        current_costs_by_task: Optional[dict[str, float]] = None,
    ) -> BaselineComparisonReport:
        """
        Compare cpm_result against the specified baseline (latest if None).

        current_costs_by_task: optional dict of task_id → actual/committed cost;
        if not supplied, cost variance is omitted from the report.
        """
        baseline: ProjectBaseline | None = (
            self._baselines.get_baseline(baseline_id)
            if baseline_id
            else self._baselines.get_latest_for_project(project_id)
        )
        if baseline is None:
            raise NotFoundError("No baseline found for comparison.", code="BASELINE_NOT_FOUND")

        baseline_tasks: list[BaselineTask] = self._baselines.list_tasks(baseline.id)
        baseline_by_task: dict[str, BaselineTask] = {bt.task_id: bt for bt in baseline_tasks}

        variances: list[TaskVariance] = []
        costs = current_costs_by_task or {}

        for task_id, info in cpm_result.items():
            bt = baseline_by_task.get(task_id)
            task_name = info.task.name

            current_start = info.earliest_start
            current_finish = info.earliest_finish
            baseline_start = bt.baseline_start if bt else None
            baseline_finish = bt.baseline_finish if bt else None

            start_var = self._working_variance(baseline_start, current_start)
            finish_var = self._working_variance(baseline_finish, current_finish)

            baseline_dur = bt.baseline_duration_days if bt else None
            current_dur = int(info.task.duration_days or 0)
            dur_var = (current_dur - baseline_dur) if baseline_dur is not None else None

            baseline_cost = float(bt.baseline_planned_cost) if bt else None
            current_cost = costs.get(task_id)
            cost_var = (current_cost - baseline_cost) if (current_cost is not None and baseline_cost is not None) else None

            is_delayed = (finish_var is not None and finish_var > 0)

            variances.append(TaskVariance(
                task_id=task_id,
                task_name=task_name,
                baseline_start=baseline_start,
                baseline_finish=baseline_finish,
                current_start=current_start,
                current_finish=current_finish,
                start_variance_days=start_var,
                finish_variance_days=finish_var,
                duration_variance_days=dur_var,
                cost_variance=cost_var,
                is_delayed=is_delayed,
                is_critical=info.is_critical,
            ))

        max_slip = max((v.finish_variance_days for v in variances if v.finish_variance_days is not None), default=0)
        total_cost_var = sum(v.cost_variance for v in variances if v.cost_variance is not None)

        return BaselineComparisonReport(
            baseline_id=baseline.id,
            baseline_name=baseline.name,
            project_id=project_id,
            compared_at=date.today(),
            task_variances=variances,
            total_schedule_slippage_days=max(0, max_slip),
            tasks_delayed=sum(1 for v in variances if v.is_delayed),
            tasks_on_time=sum(1 for v in variances if v.finish_variance_days == 0),
            tasks_early=sum(1 for v in variances if v.finish_variance_days is not None and v.finish_variance_days < 0),
            total_cost_variance=total_cost_var,
        )

    # ── internal ─────────────────────────────────────────────────────────────

    def _working_variance(
        self,
        baseline_date: date | None,
        current_date: date | None,
    ) -> int | None:
        """Positive = delayed, negative = early, 0 = on time."""
        if baseline_date is None or current_date is None:
            return None
        if current_date == baseline_date:
            return 0
        if current_date > baseline_date:
            return self._calendar.working_days_between(baseline_date, current_date) - 1
        return -(self._calendar.working_days_between(current_date, baseline_date) - 1)


__all__ = ["BaselineComparisonService", "BaselineComparisonReport", "TaskVariance"]
