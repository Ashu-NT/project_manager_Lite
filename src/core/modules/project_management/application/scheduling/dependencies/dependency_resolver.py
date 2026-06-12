from __future__ import annotations

from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

from dataclasses import dataclass
from datetime import date

from src.core.modules.project_management.domain.tasks.task import Task, TaskDependency
from src.core.modules.project_management.domain.enums import DependencyType


@dataclass
class DependencyDateResult:
    """Resolved earliest start/finish for a task given its incoming dependencies."""
    task_id: str
    earliest_start: date | None
    earliest_finish: date | None
    resolved_from: list[str]  # predecessor task IDs that drove this result


class DependencyResolver:
    """
    Stateless calculation service for dependency date resolution.

    Supports all four dependency types with lag (and negative lag = lead):
        FS  (Finish-to-Start)
        SS  (Start-to-Start)
        FF  (Finish-to-Finish)
        SF  (Start-to-Finish)

    The SchedulingEngine delegates date derivation per-task here.
    Callers supply already-computed predecessor ES/EF dicts (from the forward pass).
    """

    def __init__(self, calendar: CalendarProtocol) -> None:
        self._calendar = calendar

    def resolve_early_dates(
        self,
        task: Task,
        incoming_deps: list[TaskDependency],
        es: dict[str, date | None],
        ef: dict[str, date | None],
    ) -> DependencyDateResult:
        """
        Compute the earliest start / finish for *task* given its predecessor dates.

        For tasks without incoming dependencies the task's own start_date anchors the schedule.
        """
        duration = int(task.duration_days or 0)
        is_milestone = duration <= 0

        if not incoming_deps:
            return self._anchor_from_task(task, duration, is_milestone)

        candidate_es: list[date] = []
        drivers: list[str] = []

        for dep in incoming_deps:
            cand = self._candidate_start(dep, es, ef, duration)
            if cand is not None:
                candidate_es.append(cand)
                drivers.append(dep.predecessor_task_id)

        if not candidate_es:
            return self._anchor_from_task(task, duration, is_milestone)

        est = max(candidate_es)
        if is_milestone:
            return DependencyDateResult(task_id=task.id, earliest_start=est, earliest_finish=est, resolved_from=drivers)
        eft = self._calendar.add_working_days(est, duration)
        return DependencyDateResult(task_id=task.id, earliest_start=est, earliest_finish=eft, resolved_from=drivers)

    def resolve_late_dates_contribution(
        self,
        dep: TaskDependency,
        succ_ls: date | None,
        succ_lf: date | None,
        pred_duration: int,
    ) -> tuple[date | None, date | None]:
        """
        Return (candidate_lf, candidate_ls) that a single dependency contributes
        to the predecessor's latest dates during the backward pass.
        """
        cand_lf: date | None = None
        cand_ls: date | None = None

        if dep.dependency_type == DependencyType.FINISH_TO_START:
            if succ_ls is not None:
                cand_lf = self._calendar.add_working_days(succ_ls, -(dep.lag_days + 1))
        elif dep.dependency_type == DependencyType.FINISH_TO_FINISH:
            if succ_lf is not None:
                cand_lf = self._calendar.add_working_days(succ_lf, -dep.lag_days)
        elif dep.dependency_type == DependencyType.START_TO_START:
            if succ_ls is not None:
                cand_ls = self._calendar.add_working_days(succ_ls, -dep.lag_days)
        elif dep.dependency_type == DependencyType.START_TO_FINISH:
            if succ_lf is not None:
                cand_ls = self._calendar.add_working_days(succ_lf, -dep.lag_days)

        return cand_lf, cand_ls

    # ── internal ────────────────────────────────────────────────────────────

    def _candidate_start(
        self,
        dep: TaskDependency,
        es: dict[str, date | None],
        ef: dict[str, date | None],
        duration: int,
    ) -> date | None:
        pred_es = es.get(dep.predecessor_task_id)
        pred_ef = ef.get(dep.predecessor_task_id)

        if dep.dependency_type == DependencyType.FINISH_TO_START:
            if pred_ef:
                return self._calendar.add_working_days(pred_ef, dep.lag_days + 2)

        elif dep.dependency_type == DependencyType.START_TO_START:
            if pred_es:
                return self._calendar.add_working_days(pred_es, dep.lag_days)

        elif dep.dependency_type == DependencyType.FINISH_TO_FINISH:
            if pred_ef:
                ef_s = self._calendar.add_working_days(pred_ef, dep.lag_days)
                return self._calendar.add_working_days(ef_s, -(duration - 1)) if duration > 0 else ef_s

        elif dep.dependency_type == DependencyType.START_TO_FINISH:
            if pred_es:
                ef_s = self._calendar.add_working_days(pred_es, dep.lag_days)
                return self._calendar.add_working_days(ef_s, -(duration - 1)) if duration > 0 else ef_s

        return None

    def _anchor_from_task(
        self,
        task: Task,
        duration: int,
        is_milestone: bool,
    ) -> DependencyDateResult:
        if task.start_date:
            if is_milestone:
                return DependencyDateResult(
                    task_id=task.id,
                    earliest_start=task.start_date,
                    earliest_finish=task.start_date,
                    resolved_from=[],
                )
            eft = self._calendar.add_working_days(task.start_date, duration)
            return DependencyDateResult(
                task_id=task.id,
                earliest_start=task.start_date,
                earliest_finish=eft,
                resolved_from=[],
            )
        return DependencyDateResult(task_id=task.id, earliest_start=None, earliest_finish=None, resolved_from=[])


__all__ = ["DependencyResolver", "DependencyDateResult"]
