from __future__ import annotations

from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Set

from src.core.modules.project_management.contracts.repositories.task import (
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.modules.project_management.application.scheduling.cpm_calculator import (
    CPMCalculator,
    CPMResult,
)


@dataclass
class TaskImpact:
    task_id: str
    task_name: str
    original_start: Optional[date]
    original_finish: Optional[date]
    proposed_start: Optional[date]
    proposed_finish: Optional[date]
    start_shift_days: Optional[int]   # positive = later, negative = earlier
    finish_shift_days: Optional[int]
    is_critical: bool


@dataclass
class ScheduleChangeImpactReport:
    """
    Impact analysis for a proposed date change on a single task.

    Lists every downstream task that would shift, the magnitude of shift,
    and which tasks would join or leave the critical path.
    """
    changed_task_id: str
    proposed_start: Optional[date]
    proposed_finish: Optional[date]
    proposed_duration_days: Optional[int]
    affected_tasks: List[TaskImpact]          # tasks that shift (including the changed task)
    newly_critical_task_ids: List[str]        # tasks entering critical path
    no_longer_critical_task_ids: List[str]    # tasks leaving critical path
    max_project_finish_shift_days: int        # positive = project end delayed
    requires_approval: bool                   # true if approved baseline exists and shift > threshold


class ScheduleChangeImpactService:
    """
    Analyses the downstream impact of a proposed schedule change before persisting.

    Workflow:
        1. Caller proposes a new start/finish/duration for a task.
        2. Service runs a second CPM pass with the proposed values applied.
        3. Diffs original vs proposed CPM results to identify affected tasks.
        4. Returns an impact report the UI or approval router can act on.

    This service never writes to the database.
    """

    APPROVAL_THRESHOLD_DAYS: int = 5  # override via constructor arg

    def __init__(
        self,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        calendar: CalendarProtocol,
        approval_threshold_days: int = 5,
    ) -> None:
        self._task_repo = task_repo
        self._dependency_repo = dependency_repo
        self._calendar = calendar
        self._approval_threshold_days = approval_threshold_days
        self._cpm = CPMCalculator(calendar)

    def analyse(
        self,
        project_id: str,
        changed_task_id: str,
        proposed_start: Optional[date] = None,
        proposed_finish: Optional[date] = None,
        proposed_duration_days: Optional[int] = None,
        has_approved_baseline: bool = False,
    ) -> ScheduleChangeImpactReport:
        """
        Run two CPM passes (original vs proposed) and return the delta.

        At least one of proposed_start / proposed_finish / proposed_duration_days
        must be supplied.
        """
        tasks = self._task_repo.list_by_project(project_id)
        deps = self._dependency_repo.list_by_project(project_id)

        tasks_by_id: Dict[str, Task] = {t.id: t for t in tasks}

        # ── original pass ────────────────────────────────────────────────
        original: CPMResult = self._cpm.calculate(tasks_by_id, deps)

        # ── proposed pass (copy with the change applied) ─────────────────
        from dataclasses import replace
        proposed_tasks: Dict[str, Task] = {tid: replace(t) for tid, t in tasks_by_id.items()}
        changed = proposed_tasks.get(changed_task_id)
        if changed is None:
            return ScheduleChangeImpactReport(
                changed_task_id=changed_task_id,
                proposed_start=proposed_start,
                proposed_finish=proposed_finish,
                proposed_duration_days=proposed_duration_days,
                affected_tasks=[],
                newly_critical_task_ids=[],
                no_longer_critical_task_ids=[],
                max_project_finish_shift_days=0,
                requires_approval=False,
            )
        if proposed_start is not None:
            changed.start_date = proposed_start
        if proposed_finish is not None:
            changed.end_date = proposed_finish
        if proposed_duration_days is not None:
            changed.duration_days = proposed_duration_days

        proposed: CPMResult = self._cpm.calculate(proposed_tasks, deps)

        # ── diff ─────────────────────────────────────────────────────────
        affected: List[TaskImpact] = []
        orig_critical: Set[str] = set(original.critical_path_task_ids)
        prop_critical: Set[str] = set(proposed.critical_path_task_ids)

        for task_id in tasks_by_id:
            orig_info = original.schedule.get(task_id)
            prop_info = proposed.schedule.get(task_id)
            if orig_info is None or prop_info is None:
                continue

            orig_s = orig_info.earliest_start
            orig_f = orig_info.earliest_finish
            prop_s = prop_info.earliest_start
            prop_f = prop_info.earliest_finish

            start_shift = self._day_shift(orig_s, prop_s)
            finish_shift = self._day_shift(orig_f, prop_f)

            if start_shift == 0 and finish_shift == 0 and task_id != changed_task_id:
                continue  # unaffected

            affected.append(TaskImpact(
                task_id=task_id,
                task_name=tasks_by_id[task_id].name,
                original_start=orig_s,
                original_finish=orig_f,
                proposed_start=prop_s,
                proposed_finish=prop_f,
                start_shift_days=start_shift,
                finish_shift_days=finish_shift,
                is_critical=(task_id in prop_critical),
            ))

        orig_ef = original.project_early_finish
        prop_ef = proposed.project_early_finish
        project_finish_shift = self._day_shift(orig_ef, prop_ef)

        newly_critical = sorted(prop_critical - orig_critical)
        no_longer_critical = sorted(orig_critical - prop_critical)

        requires_approval = (
            has_approved_baseline
            and abs(project_finish_shift) >= self._approval_threshold_days
        )

        return ScheduleChangeImpactReport(
            changed_task_id=changed_task_id,
            proposed_start=proposed_start,
            proposed_finish=proposed_finish,
            proposed_duration_days=proposed_duration_days,
            affected_tasks=affected,
            newly_critical_task_ids=newly_critical,
            no_longer_critical_task_ids=no_longer_critical,
            max_project_finish_shift_days=project_finish_shift,
            requires_approval=requires_approval,
        )

    # ── internal ─────────────────────────────────────────────────────────────

    def _day_shift(self, original: Optional[date], proposed: Optional[date]) -> int:
        if original is None or proposed is None:
            return 0
        if proposed == original:
            return 0
        if proposed > original:
            return self._calendar.working_days_between(original, proposed) - 1
        return -(self._calendar.working_days_between(proposed, original) - 1)


__all__ = ["ScheduleChangeImpactService", "ScheduleChangeImpactReport", "TaskImpact"]
